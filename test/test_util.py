# encoding=utf-8
from __future__ import print_function
import unittest
import time
from mwclient.util import parse_timestamp

if __name__ == "__main__":
    print()
    print("Note: Running in stand-alone mode. Consult the README")
    print("      (section 'Contributing') for advice on running tests.")
    print()


class TestUtil(unittest.TestCase):

    def test_parse_missing_timestamp(self):
        assert time.struct_time((0, 0, 0, 0, 0, 0, 0, 0, 0)) == parse_timestamp(None)

    def test_parse_empty_timestamp(self):
        assert time.struct_time((0, 0, 0, 0, 0, 0, 0, 0, 0)) == parse_timestamp('0000-00-00T00:00:00Z')

    def test_parse_nonempty_timestamp(self):
        assert time.struct_time((2015, 1, 2, 20, 18, 36, 4, 2, -1)) == parse_timestamp('2015-01-02T20:18:36Z')

if __name__ == '__main__':
    unittest.main()
