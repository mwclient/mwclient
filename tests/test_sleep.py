# encoding=utf-8
from __future__ import print_function
import unittest
import time
import mock
import pytest
from mwclient.sleep import Sleepers
from mwclient.sleep import Sleeper
from mwclient.errors import MaximumRetriesExceeded

if __name__ == "__main__":
    print()
    print("Note: Running in stand-alone mode. Consult the README")
    print("      (section 'Contributing') for advice on running tests.")
    print()


class TestSleepers(unittest.TestCase):

    def setUp(self):
        self.sleep = mock.patch('time.sleep').start()
        self.max_retries = 10
        self.sleepers = Sleepers(self.max_retries, 30)

    def tearDown(self):
        mock.patch.stopall()

    def test_make(self):
        sleeper = self.sleepers.make()
        assert type(sleeper) == Sleeper
        assert sleeper.retries == 0

    def test_sleep(self):
        sleeper = self.sleepers.make()
        sleeper.sleep()
        sleeper.sleep()
        self.sleep.assert_has_calls([mock.call(0), mock.call(30)])

    def test_min_time(self):
        sleeper = self.sleepers.make()
        sleeper.sleep(5)
        self.sleep.assert_has_calls([mock.call(5)])

    def test_retries_count(self):
        sleeper = self.sleepers.make()
        sleeper.sleep()
        sleeper.sleep()
        assert sleeper.retries == 2

    def test_max_retries(self):
        sleeper = self.sleepers.make()
        for x in range(self.max_retries):
            sleeper.sleep()
        with pytest.raises(MaximumRetriesExceeded):
            sleeper.sleep()

if __name__ == '__main__':
    unittest.main()
