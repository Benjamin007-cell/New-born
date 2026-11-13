import unittest
from disclosure.research import decode
from disclosure.silver import weak_label
class ResearchTests(unittest.TestCase):
    def test_decoder_uses_exact_character_offsets(self):
        text='Debt ratio. Revenue.'
        entities=decode([0,1,2,2,0,0],[(0,0),(0,4),(5,10),(10,11),(12,19),(0,0)],text)
        self.assertEqual(entities,[{'start':0,'end':11,'label':'COVENANT','text':'Debt ratio.'}])
    def test_i_tag_repaired_and_label_change_separated(self):
        self.assertEqual([e['label'] for e in decode([2,4],[(0,4),(5,9)],'Debt cash')],['COVENANT','FX_SENSITIVITY'])
    def test_weak_rules_reject_generic_risk_and_civil_covenants(self):
        self.assertIsNone(weak_label('Foreign currency risk may affect our operations.'))
        self.assertIsNone(weak_label('The international covenant on civil and political rights governs this policy.'))
        self.assertEqual(weak_label('A 10% change in exchange rates would reduce profit.'),'FX_SENSITIVITY')
        self.assertEqual(weak_label('We complied with our debt covenants.'),'COVENANT')

class SplitTests(unittest.TestCase):
    def test_frozen_files_reject_edits(self):
        import hashlib,json,tempfile
        from pathlib import Path
        from disclosure.research import verify_split_files
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); manifest={'sources':[],'splits':{}}
            for name in ['train','validation','test']:
                data=(name+'\n').encode();(root/(name+'.jsonl')).write_bytes(data)
                manifest['splits'][name]={'sha256':hashlib.sha256(data).hexdigest()}
                manifest['sources'].append({'split':name,'issuer':name})
            (root/'split-manifest.json').write_text(json.dumps(manifest))
            verify_split_files(root)
            (root/'test.jsonl').write_text('changed')
            with self.assertRaises(ValueError):verify_split_files(root)
    def test_issuer_overlap_rejected(self):
        import hashlib,json,tempfile
        from pathlib import Path
        from disclosure.research import verify_split_files
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); manifest={'sources':[],'splits':{}}
            for name in ['train','validation','test']:
                (root/(name+'.jsonl')).write_text('')
                manifest['splits'][name]={'sha256':hashlib.sha256(b'').hexdigest()}
                manifest['sources'].append({'split':name,'issuer':'same'})
            (root/'split-manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):verify_split_files(root)

class WeakPolicyRegressionTests(unittest.TestCase):
    def test_exposure_amounts_are_not_sensitivity_shocks(self):
        self.assertIsNone(weak_label('Foreign exchange contracts and interest rate contracts represented 38% of receivables and fair value assets.'))
    def test_accounting_classification_is_not_a_specific_debt_covenant(self):
        self.assertIsNone(weak_label('Such covenants affect classification at the reporting period even if compliance is assessed after the reporting date.'))
