import json
from pathlib import Path
import tempfile
import unittest
from disclosure.core import baseline, metrics, read_records
from disclosure.train import encode_record
class CoreTests(unittest.TestCase):
    def test_offsets(self):
        text = '  The debt covenant restricts distributions. Currency risk increased.'
        e = baseline(text)
        self.assertEqual([x['label'] for x in e], ['COVENANT', 'FX_SENSITIVITY'])
        self.assertTrue(all(text[x['start']:x['end']] == x['text'] for x in e))
    def test_exact_match(self):
        g = [{'id':'a','text':'abcdef','entities':[{'start':0,'end':3,'label':'COVENANT'}]}]
        p = [{'id':'a','text':'abcdef','entities':[{'start':0,'end':2,'label':'COVENANT'}]}]
        self.assertEqual(metrics(g,g)['f1'], 1)
        self.assertEqual(metrics(g,p)['f1'], 0)
        with self.assertRaises(ValueError): metrics(g, [])
    def test_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.jsonl'
            p.write_text(json.dumps({'id':'a','text':'abcdef','entities':[{'start':0,'end':4,'label':'COVENANT'},{'start':2,'end':5,'label':'AUDIT_NOTE'}]}))
            with self.assertRaises(ValueError): read_records(p)
    def test_subword_alignment(self):
        class Tokenizer:
            model_max_length=512
            def __call__(self,*args,**kwargs):
                return {'input_ids':[101,1,2,102], 'offset_mapping':[(0,0),(0,3),(3,6),(0,0)]}
        row={'id':'a','text':'abcdef','entities':[{'start':0,'end':6,'label':'COVENANT'}]}
        self.assertEqual(encode_record(row,Tokenizer())['labels'],[-100,1,2,-100])
        row['entities'][0]['start']=1
        with self.assertRaises(ValueError): encode_record(row,Tokenizer())
