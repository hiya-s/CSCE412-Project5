import unittest
from agents.tools import check_local_site
from agents.core import validate

class TestProject(unittest.TestCase):
    def test_site(self):
        self.assertTrue(check_local_site()['ok'])
    def test_missing_fields_fail(self):
        with self.assertRaises(ValueError): validate('requirements', {'summary':'x'})
    def test_valid_requirements(self):
        output={'summary':'x','pages':['a','b','c','d','e'],'services':[], 'security_requirements':[], 'questions':[]}
        self.assertEqual(validate('requirements',output),output)
if __name__=='__main__':unittest.main()
