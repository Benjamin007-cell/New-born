"""Offline integration check only: random tiny BERT and synthetic fixtures."""
import argparse
import json
from pathlib import Path
from transformers import BertConfig, BertForTokenClassification, BertTokenizerFast, pipeline, set_seed
from disclosure import LABELS
from disclosure.train import train
from disclosure.core import write_jsonl

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);a=p.parse_args()
    root=a.directory.resolve(); base=root/'tiny-base';base.mkdir(parents=True,exist_ok=True)
    set_seed(42)
    vocab=['[PAD]','[UNK]','[CLS]','[SEP]','[MASK]','the','debt','covenant','limits','borrowing','currency','sensitivity','reduces','profit','auditor','reported','a','qualified','opinion','.','this','loan','restricts','dividends','exchange','rate','affects','earnings','audit','note','describes','risk']
    (base/'vocab.txt').write_text('\n'.join(vocab)+'\n')
    tok=BertTokenizerFast(vocab_file=str(base/'vocab.txt'),model_max_length=128);tok.save_pretrained(base)
    config=BertConfig(vocab_size=len(vocab),hidden_size=32,num_hidden_layers=1,num_attention_heads=2,intermediate_size=64,num_labels=len(LABELS),id2label=dict(enumerate(LABELS)),label2id={v:i for i,v in enumerate(LABELS)})
    BertForTokenClassification(config).save_pretrained(base)
    def record(i,text,label,doc):
        return {'id':i,'text':text,'source_document':doc,'annotation_status':'reviewed','annotation_method':'synthetic-code-fixture','entities':[{'start':0,'end':len(text),'label':label}]}
    training=[record('t1','the debt covenant limits borrowing.','COVENANT','synthetic-train'),record('t2','currency sensitivity reduces profit.','FX_SENSITIVITY','synthetic-train'),record('t3','the auditor reported a qualified opinion.','AUDIT_NOTE','synthetic-train')]
    validation=[record('v1','this loan restricts dividends.','COVENANT','synthetic-validation'),record('v2','the exchange rate affects earnings.','FX_SENSITIVITY','synthetic-validation'),record('v3','the audit note describes risk.','AUDIT_NOTE','synthetic-validation')]
    write_jsonl(root/'train.jsonl',training);write_jsonl(root/'validation.jsonl',validation)
    train(root/'train.jsonl',root/'validation.jsonl',str(root/'saved'),str(base),1)
    extractor=pipeline('token-classification',model=str(root/'saved'),tokenizer=str(root/'saved'),aggregation_strategy='simple',device=-1)
    result=extractor(validation[0]['text'])
    summary={'status':'passed','purpose':'Synthetic integration test, NOT a financial model or benchmark','train_records':3,'validation_records':3,'prediction_spans':len(result),'saved_model_reloaded':True}
    (root/'smoke-result.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))

if __name__=='__main__':main()
