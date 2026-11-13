"""Class-weighted research training on explicitly weak labels and sealed test data."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from . import LABELS
from .core import read_records,write_jsonl,evaluation_report
from .train import encode_record

def decode(ids,offsets,text):
    entities=[];current=None
    def flush():
        nonlocal current
        if current:
            current['text']=text[current['start']:current['end']];entities.append(current);current=None
    for tag_id,(start,end) in zip(ids,offsets):
        if start==end:continue
        tag=LABELS[int(tag_id)]
        if tag=='O':flush();continue
        prefix,label=tag.split('-',1)
        if prefix=='B' or current is None or current['label']!=label:
            flush();current={'start':start,'end':end,'label':label}
        else:current['end']=end
    flush();return entities

def verify_split_files(root):
    manifest=json.loads((root/'split-manifest.json').read_text())
    for name in ['train','validation','test']:
        digest=hashlib.sha256((root/(name+'.jsonl')).read_bytes()).hexdigest()
        if digest!=manifest['splits'][name]['sha256']:raise ValueError('Split changed after freezing')
    issuers={name:{s['issuer'].strip().casefold() for s in manifest['sources'] if s['split']==name} for name in ['train','validation','test']}
    if any(issuers[a]&issuers[b] for a,b in [('train','validation'),('train','test'),('validation','test')]):raise ValueError('Issuer leakage in manifest')
    return manifest

def train_research(corpus,output,base,epochs=12):
    import numpy as np
    import torch
    from datasets import Dataset
    from transformers import AutoTokenizer,AutoModelForTokenClassification,DataCollatorForTokenClassification,Trainer,TrainingArguments,set_seed
    root=Path(corpus);out=Path(output)
    if out.exists() and any(out.iterdir()):raise ValueError('Use a new output directory')
    manifest=verify_split_files(root)
    # No test labels or text are loaded during model training/selection.
    rows=read_records(root/'train.jsonl');val=read_records(root/'validation.jsonl')
    if not rows or not val:raise ValueError('Empty split')
    if any(r.get('annotation_status')!='weak' for r in rows+val):raise ValueError('This entry point is explicitly for weak-label research')
    if {r['issuer'] for r in rows}&{r['issuer'] for r in val}:raise ValueError('Issuer leakage')
    if {r['source_document'] for r in rows}&{r['source_document'] for r in val}:raise ValueError('Document leakage')
    if {r['text'] for r in rows}&{r['text'] for r in val}:raise ValueError('Duplicate text across splits')
    set_seed(42);torch.set_num_threads(2)
    tok=AutoTokenizer.from_pretrained(base,use_fast=True)
    encoded=[encode_record(r,tok) for r in rows]
    counts=Counter(tag for e in encoded for tag in e['labels'] if tag!=-100)
    # Inverse square-root weighting; absent tags get zero weight and are reported.
    weights=torch.tensor([1/(counts[i]**0.5) if counts[i] else 0 for i in range(len(LABELS))],dtype=torch.float)
    weights=weights/weights[weights>0].mean()
    val_encoded=[encode_record(r,tok) for r in val]
    offsets=[tok(r['text'],return_offsets_mapping=True)['offset_mapping'] for r in val]
    def metric(prediction):
        ids=np.argmax(prediction.predictions,axis=-1)
        predicted=[dict(r,entities=decode(tags,off,r['text'])) for r,tags,off in zip(val,ids,offsets)]
        report=evaluation_report(val,predicted)
        return {'f1':report['overall']['f1'],'precision':report['overall']['precision'],'recall':report['overall']['recall']}
    class WeightedTrainer(Trainer):
        def compute_loss(self,model,inputs,return_outputs=False,num_items_in_batch=None):
            labels=inputs['labels'];outputs=model(**{k:v for k,v in inputs.items() if k!='labels'})
            loss=torch.nn.functional.cross_entropy(outputs.logits.reshape(-1,len(LABELS)),labels.reshape(-1),weight=weights.to(outputs.logits.device),ignore_index=-100)
            return (loss,outputs) if return_outputs else loss
    model=AutoModelForTokenClassification.from_pretrained(base,num_labels=len(LABELS),id2label=dict(enumerate(LABELS)),label2id={v:i for i,v in enumerate(LABELS)})
    args=TrainingArguments(output_dir=str(out),learning_rate=5e-5,num_train_epochs=epochs,per_device_train_batch_size=8,per_device_eval_batch_size=8,weight_decay=.01,warmup_ratio=.1,eval_strategy='epoch',save_strategy='epoch',save_total_limit=2,load_best_model_at_end=True,metric_for_best_model='f1',greater_is_better=True,report_to='none',logging_strategy='epoch',seed=42,dataloader_pin_memory=False)
    trainer=WeightedTrainer(model=model,args=args,train_dataset=Dataset.from_list(encoded),eval_dataset=Dataset.from_list(val_encoded),data_collator=DataCollatorForTokenClassification(tok),processing_class=tok,compute_metrics=metric)
    trainer.train();trainer.save_model(str(out));tok.save_pretrained(str(out))
    summary={'annotation_quality':'WEAK RULE LABELS, NOT HUMAN GOLD','epochs':epochs,'seed':42,'learning_rate':5e-5,'token_class_counts':{LABELS[i]:counts[i] for i in range(len(LABELS))},'class_weights':weights.tolist(),'best_checkpoint':trainer.state.best_model_checkpoint,'best_validation_f1':trainer.state.best_metric,'history':trainer.state.log_history,'frozen_splits':manifest,'test_used_for_selection':False}
    (out/'research-run.json').write_text(json.dumps(summary,indent=2))
    return summary

def evaluate_test(corpus,model_path,output):
    import torch
    from transformers import AutoTokenizer,AutoModelForTokenClassification
    root=Path(corpus);out=Path(output)
    if out.exists():raise ValueError('Test report already exists; do not repeatedly tune on test results')
    manifest=verify_split_files(root);rows=read_records(root/'test.jsonl')
    torch.set_num_threads(2);tok=AutoTokenizer.from_pretrained(model_path);model=AutoModelForTokenClassification.from_pretrained(model_path).eval()
    predicted=[]
    for r in rows:
        encoded=tok(r['text'],return_offsets_mapping=True,return_tensors='pt',truncation=False)
        if encoded['input_ids'].shape[1]>min(tok.model_max_length,512):raise ValueError('Overlength record')
        offsets=encoded.pop('offset_mapping')[0].tolist()
        with torch.inference_mode():ids=model(**encoded).logits.argmax(-1)[0].tolist()
        predicted.append(dict(r,entities=decode(ids,offsets,r['text'])))
    report=evaluation_report(rows,predicted)
    report.update({'annotation_quality':'WEAK RULE LABELS, NOT INDEPENDENT HUMAN GOLD','test_records':len(rows),'test_issuers':sorted({r['issuer'] for r in rows}),'test_sha256':manifest['splits']['test']['sha256'],'test_used_for_selection':False,'warning':'This measures agreement with a heuristic labeling policy on one held-out issuer, not verified real-world accuracy. It cannot substantiate the original 88.4% claim.'})
    write_jsonl(out.with_suffix('.predictions.jsonl'),predicted)
    out.write_text(json.dumps(report,indent=2));return report

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    t=sub.add_parser('train');t.add_argument('corpus');t.add_argument('output');t.add_argument('--base',required=True);t.add_argument('--epochs',type=int,default=12)
    e=sub.add_parser('test');e.add_argument('corpus');e.add_argument('model');e.add_argument('output')
    a=p.parse_args();result=train_research(a.corpus,a.output,a.base,a.epochs) if a.action=='train' else evaluate_test(a.corpus,a.model,a.output)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
