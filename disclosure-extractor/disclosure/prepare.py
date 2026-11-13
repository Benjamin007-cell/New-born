"""Prepare bounded-length, traceable review candidates from a PDF or DOCX filing."""
import argparse
import hashlib
import re
import zipfile
from xml.etree import ElementTree
from pathlib import Path
from .core import baseline, write_jsonl

RULES = {'COVENANT': r'\bcovenants?\b|debt.service.coverage|leverage ratio',
         'FX_SENSITIVITY': r'exchange rate|foreign exchange|currency risk|sensitivity',
         'AUDIT_NOTE': r'key audit matter|critical audit matter|going concern|audit opinion|opinion on the financial'}

def chunks(text, limit=900):
    if limit < 100:
        raise ValueError('Character limit must be at least 100')
    normalized = re.sub(r'\s+', ' ', text).strip()
    start = 0
    while start < len(normalized):
        end = min(start + limit, len(normalized))
        if end < len(normalized):
            split = normalized.rfind(' ', start, end)
            if split > start: end = split
        yield start, normalized[start:end]
        start = end
        while start < len(normalized) and normalized[start] == ' ': start += 1

def prepare(path, document, issuer, url, per_category=8):
    path = Path(path)
    if per_category <= 0: raise ValueError('per-category must be positive')
    if path.suffix.lower() == '.pdf':
        from pypdf import PdfReader
        units = [(str(i+1), page.extract_text() or '') for i,page in enumerate(PdfReader(path).pages)]
        unit_name = 'page'
    elif path.suffix.lower() == '.docx':
        with zipfile.ZipFile(path) as z:
            tree = ElementTree.fromstring(z.read('word/document.xml'))
        ns = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        units = [(str(i+1), ''.join(t.text or '' for t in p.findall('.//w:t',ns))) for i,p in enumerate(tree.findall('.//w:body//w:p',ns))]
        unit_name = 'paragraph'
    else: raise ValueError('Use .pdf or .docx')
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    buckets = {k:[] for k in list(RULES) + ['NEGATIVE_CANDIDATE']}
    seen = set()
    for unit, text in units:
        for offset, fragment in chunks(text):
            if len(fragment) < 100 or fragment in seen: continue
            seen.add(fragment)
            matched = [label for label,pattern in RULES.items() if re.search(pattern,fragment,re.I)]
            category = matched[0] if matched else 'NEGATIVE_CANDIDATE'
            if len(buckets[category]) >= per_category: continue
            buckets[category].append({'id':f'{document}:{unit}:{offset}', 'source_document':document, 'issuer':issuer, 'source_url':url, 'source_sha256':sha, unit_name:int(unit), 'normalized_unit_offset':offset, 'text':fragment, 'entities':baseline(fragment), 'annotation_status':'unreviewed', 'selection_category':category, 'suggestion_method':'keyword-baseline-v1'})
    rows = [r for bucket in buckets.values() for r in bucket]
    if not rows: raise ValueError('No usable text extracted')
    return rows

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input');p.add_argument('output');p.add_argument('--document',required=True);p.add_argument('--issuer',required=True);p.add_argument('--url',required=True);p.add_argument('--per-category',type=int,default=8)
    a=p.parse_args(); rows=prepare(a.input,a.document,a.issuer,a.url,a.per_category);write_jsonl(a.output,rows)
    print('Prepared {} UNREVIEWED candidates'.format(len(rows)))

if __name__=='__main__': main()
