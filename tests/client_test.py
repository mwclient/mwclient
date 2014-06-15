# encoding=utf-8
import unittest
import sys
import os
myPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, myPath + '/../')

from mwclient import Site


class TestClient(unittest.TestCase):

    def setUp(self):
        pass

    def test_setup(self):
        # Check that templates can be found
        site = Site('commons.wikimedia.org')
        self.assertTrue(site.initialized)

if __name__ == '__main__':
    unittest.main()
