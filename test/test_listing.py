# encoding=utf-8
from __future__ import print_function

import unittest
import pytest
import logging
import requests
import responses
import mock
import mwclient
from mwclient.listing import List, GeneratorList

try:
    import json
except ImportError:
    import simplejson as json

if __name__ == "__main__":
    print()
    print("Note: Running in stand-alone mode. Consult the README")
    print("      (section 'Contributing') for advice on running tests.")
    print()


class TestList(unittest.TestCase):

    def setUp(self):
        pass

    def setupDummyResponses(self, mock_site, result_member, ns=None):
        if ns is None:
            ns = [0, 0, 0]
        mock_site.get.side_effect = [
            {
                'continue': {
                    'apcontinue': 'Kre_Mbaye',
                    'continue': '-||'
                },
                'query': {
                    result_member: [
                        {
                            "pageid": 19839654,
                            "ns": ns[0],
                            "title": "Kre'fey",
                        },
                        {
                            "pageid": 19839654,
                            "ns": ns[1],
                            "title": "Kre-O",
                        }
                    ]
                }
            },
            {
                'query': {
                    result_member: [
                        {
                            "pageid": 30955295,
                            "ns": ns[2],
                            "title": "Kre-O Transformers",
                        }
                    ]
                }
            },
        ]

    @mock.patch('mwclient.client.Site')
    def test_list_continuation(self, mock_site):
        # Test that the list fetches all three responses
        # and yields dicts when return_values not set

        lst = List(mock_site, 'allpages', 'ap', limit=2)
        self.setupDummyResponses(mock_site, 'allpages')
        vals = [x for x in lst]

        assert len(vals) == 3
        assert type(vals[0]) == dict

    @mock.patch('mwclient.client.Site')
    def test_list_with_str_return_value(self, mock_site):
        # Test that the List yields strings when return_values is string

        lst = List(mock_site, 'allpages', 'ap', limit=2, return_values='title')
        self.setupDummyResponses(mock_site, 'allpages')
        vals = [x for x in lst]

        assert len(vals) == 3
        assert type(vals[0]) == str

    @mock.patch('mwclient.client.Site')
    def test_list_with_tuple_return_value(self, mock_site):
        # Test that the List yields tuples when return_values is tuple

        lst = List(mock_site, 'allpages', 'ap', limit=2,
                   return_values=('title', 'ns'))
        self.setupDummyResponses(mock_site, 'allpages')
        vals = [x for x in lst]

        assert len(vals) == 3
        assert type(vals[0]) == tuple

    @mock.patch('mwclient.client.Site')
    def test_generator_list(self, mock_site):
        # Test that the GeneratorList yields Page objects

        lst = GeneratorList(mock_site, 'pages', 'p')
        self.setupDummyResponses(mock_site, 'pages', ns=[0, 6, 14])
        vals = [x for x in lst]

        assert len(vals) == 3
        assert type(vals[0]) == mwclient.page.Page
        assert type(vals[1]) == mwclient.image.Image
        assert type(vals[2]) == mwclient.listing.Category

if __name__ == '__main__':
    unittest.main()
