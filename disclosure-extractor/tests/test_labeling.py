import csv
import json
import tempfile
import unittest
from pathlib import Path
from disclosure.labeling import export_sheet, import_sheet
from disclosure.core import evaluation_report, read_records

class LabelingTests(unittest.TestCase):
    def test_review_and_exact_text_required(self):
        with tempfile.TemporaryDirectory() as d:
            source, sheet, output = [Path(d)/n for n in ['source.jsonl','labels.csv','gold.jsonl']]
            source.write_text(json.dumps({'id':'one','source_document':'report','text':'Debt covenant.','entities':[]}))
            export_sheet(source,sheet)
            with self.assertRaises(ValueError): import_sheet(source,sheet,output)
            with sheet.open(newline='') as f:
                reader=csv.DictReader(f); fields=reader.fieldnames; rows=list(reader)
            rows[0]['reviewed']='yes'
            rows[0]['entities_json']=json.dumps([{'start':0,'end':13,'label':'COVENANT','text':'Debt covenant'}])
            with sheet.open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader();writer.writerows(rows)
            import_sheet(source,sheet,output)
            gold=read_records(output)
            report=evaluation_report(gold,gold)
            self.assertEqual(report['per_class']['COVENANT']['f1'],1)
            self.assertEqual(report['overall']['gold_entities'],1)
            rows[0]['text']='Modified'
            with sheet.open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
            with self.assertRaises(ValueError): import_sheet(source,sheet,output)
