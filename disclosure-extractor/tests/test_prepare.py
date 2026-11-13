import unittest
from disclosure.prepare import chunks
class PrepareTests(unittest.TestCase):
    def test_bounds_and_unicode(self):
        original=' '.join(['Foreign exchange ₦ exposure.']*50)
        pieces=list(chunks(original,120))
        self.assertTrue(all(len(t)<=120 for _,t in pieces))
        self.assertTrue(all(original[offset:offset+len(text)]==text for offset,text in pieces))
        self.assertEqual(' '.join(t for _,t in pieces),original)
    def test_long_word(self):
        self.assertEqual(''.join(t for _,t in chunks('x'*250,100)),'x'*250)
