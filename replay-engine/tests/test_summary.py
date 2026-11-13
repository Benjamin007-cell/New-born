import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from replay import summarize
class SummaryTests(unittest.TestCase):
    def test_weighted_average_and_fees(self):
        s = summarize('timestamp,maker,taker,price,quantity,maker_fee,taker_fee\n1,a,b,100,2,-0.01,0.02\n2,c,d,110,1,0,0.03\n')
        self.assertEqual(s['quantity'], 3)
        self.assertEqual(s['total_fees'], '0.04')
        self.assertTrue(s['vwap_minor_units'].startswith('103.333'))
    def test_empty(self):
        self.assertIsNone(summarize('timestamp,maker,taker,price,quantity,maker_fee,taker_fee\n')['vwap_minor_units'])
