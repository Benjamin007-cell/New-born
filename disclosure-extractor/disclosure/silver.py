"""Deterministic weak-label research corpus builder. These labels are NOT gold."""
import argparse
import hashlib
import json
import random
import re
import zipfile
from collections import Counter,defaultdict
from pathlib import Path
from xml.etree import ElementTree
from .core import write_jsonl

POLICY_VERSION='silver-sentence-v2'

def weak_label(text):
    lower=text.lower()
    if re.search(r'\bcovenants?\b|debt.service.coverage ratio|net.debt.to.ebitda',lower):
        if re.search(r'\b(debt|loan|borrow|credit|financ|indenture|restrict|breach|compli|ratio|default)',lower) and not re.search(r'\b(ias|ifrs|human rights|civil|political|amendments|classification|reporting period|right exists)\b',lower):
            return 'COVENANT'
    if re.search(r'foreign currenc|foreign exchange|exchange rate|naira|currency rate',lower) and re.search(r'\d\s*%|percent|per cent',lower) and re.search(r'profit|earnings|equity|income|fair value|loss|sensitivity',lower) and re.search(r'\b(?:increas|decreas|appreciat|depreciat|strengthen|weaken|chang|sensitiv)\w*\b',lower):
        return 'FX_SENSITIVITY'
    if re.search(r'key audit matter|critical audit matter|qualified opinion|adverse opinion|disclaimer of opinion|material uncertainty related to going concern',lower):
        return 'AUDIT_NOTE'
    if re.search(r'in our opinion|we have audited|our audit opinion',lower) and re.search(r'financial statements|financial position|fairly|true and fair',lower):
        return 'AUDIT_NOTE'
    return None

def text_units(path):
    path=Path(path)
    if path.suffix.lower()=='.pdf':
        from pypdf import PdfReader
        for i,page in enumerate(PdfReader(path).pages):yield 'page',i+1,page.extract_text() or ''
    elif path.suffix.lower()=='.docx':
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        with zipfile.ZipFile(path) as archive:tree=ElementTree.fromstring(archive.read('word/document.xml'))
        for i,p in enumerate(tree.findall('.//w:body//w:p',ns)):
            yield 'paragraph',i+1,' '.join(t.text or '' for t in p.findall('.//w:t',ns))
        for i,row in enumerate(tree.findall('.//w:tbl/w:tr',ns)):
            yield 'table_row',i+1,' '.join(t.text or '' for t in row.findall('.//w:t',ns))
    else:raise ValueError('Expected PDF or DOCX')

def build(manifest_path,output):
    sources=json.loads(Path(manifest_path).read_text())
    if {s['split'] for s in sources}!={'train','validation','test'}:raise ValueError('Need train, validation and test sources')
    issuer_split={}
    for source in sources:
        key=source['issuer'].strip().casefold()
        if key in issuer_split and issuer_split[key]!=source['split']:raise ValueError('Issuer leakage')
        issuer_split[key]=source['split']
    buckets=defaultdict(list);seen={};source_summaries=[]
    for source in sources:
        sha=hashlib.sha256(Path(source['path']).read_bytes()).hexdigest()
        source_summaries.append({k:v for k,v in dict(source,sha256=sha).items() if k!='path'})
        for kind,unit,text in text_units(source['path']):
            text=re.sub(r'\s+',' ',text).strip()
            # Split sentence endings before uppercase starts, preserving decimal numbers.
            for j,sentence in enumerate(re.split(r'(?<=[.!?])\s+(?=[A-Z“(])',text)):
                sentence=sentence.strip()
                if not 40<=len(sentence)<=1000 or len(sentence.split())<8:continue
                normalized=re.sub(r'\W+',' ',sentence.lower()).strip()
                digest=hashlib.sha256(normalized.encode()).hexdigest()
                # Deduplicate across the ENTIRE corpus, assigning shared boilerplate to its first source only.
                if digest in seen:continue
                seen[digest]=source['split']
                label=weak_label(sentence)
                record={'id':f"{source['document']}:{kind}:{unit}:{j}",'source_document':source['document'],'issuer':source['issuer'],'source_url':source['url'],'source_sha256':sha,kind:unit,'text':sentence,'entities':[],'annotation_status':'weak','annotation_method':POLICY_VERSION,'independent_human_review':False}
                if label:record['entities']=[{'start':0,'end':len(sentence),'label':label,'text':sentence}]
                # Preserve harder negatives with relevant words rather than only boilerplate.
                negative='hard-negative' if re.search(r'audit|currency|exchange|loan|debt|ratio|covenant|profit',sentence,re.I) else 'negative'
                buckets[(source['split'],source['document'],label or negative)].append(record)
    rng=random.Random(42);splits={k:[] for k in ['train','validation','test']}
    for (split,document,label),records in sorted(buckets.items()):
        rng.shuffle(records)
        cap=30 if label in {'COVENANT','FX_SENSITIVITY','AUDIT_NOTE'} else (25 if label=='hard-negative' else 10)
        splits[split].extend(records[:cap])
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    summary={'policy':POLICY_VERSION,'annotation_quality':'weak rule labels, NOT independent gold','sources':source_summaries,'splits':{}}
    for split,records in splits.items():
        if split == 'train':
            positives = [r for r in records if r['entities']]
            negatives = [r for r in records if not r['entities']]
            rng.shuffle(negatives)
            records = positives + negatives[:len(positives)]
        rng.shuffle(records);write_jsonl(root/(split+'.jsonl'),records)
        summary['splits'][split]={'records':len(records),'entities':dict(Counter(e['label'] for r in records for e in r['entities'])),'negative_records':sum(not r['entities'] for r in records),'sha256':hashlib.sha256((root/(split+'.jsonl')).read_bytes()).hexdigest()}
    (root/'split-manifest.json').write_text(json.dumps(summary,indent=2))
    return summary

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest');p.add_argument('output');a=p.parse_args();print(json.dumps(build(a.manifest,a.output),indent=2))
if __name__=='__main__':main()
