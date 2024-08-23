import unittest
import pytest
import mwclient
from mwclient.listing import List, GeneratorList

import unittest.mock as mock


if __name__ == "__main__":
    print()
    print("Note: Running in stand-alone mode. Consult the README")
    print("      (section 'Contributing') for advice on running tests.")
    print()


class TestList(unittest.TestCase):

    def setUp(self):
        pass

    def setupDummyResponsesOne(self, mock_site, result_member, ns=None):
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
                    ]
                }
            },
            {
                'continue': {
                    'apcontinue': 'Kre_Blip',
                    'continue': '-||'
                },
                'query': {
                    result_member: [
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

    def setupDummyResponsesTwo(self, mock_site, result_member, ns=None):
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

        lst = List(mock_site, 'allpages', 'ap', api_chunk_size=2)
        self.setupDummyResponsesTwo(mock_site, 'allpages')
        vals = [x for x in lst]

        assert len(vals) == 3
        assert type(vals[0]) == dict
        assert lst.args["aplimit"] == "2"
        assert mock_site.get.call_count == 2

    @mock.patch('mwclient.client.Site')
    def test_list_limit_deprecated(self, mock_site):
        # Test that the limit arg acts as api_chunk_size but generates
        # DeprecationWarning

        with pytest.deprecated_call():
            lst = List(mock_site, 'allpages', 'ap', limit=2)
        self.setupDummyResponsesTwo(mock_site, 'allpages')
        vals = [x for x in lst]

        assert len(vals) == 3
        assert type(vals[0]) == dict
        assert lst.args["aplimit"] == "2"
        assert mock_site.get.call_count == 2

    @mock.patch('mwclient.client.Site')
    def test_list_max_items(self, mock_site):
        # Test that max_items properly caps the list
        # iterations

        mock_site.api_limit = 500
        lst = List(mock_site, 'allpages', 'ap', max_items=2)
        self.setupDummyResponsesTwo(mock_site, 'allpages')
        vals = [x for x in lst]

        assert len(vals) == 2
        assert type(vals[0]) == dict
        assert lst.args["aplimit"] == "2"
        assert mock_site.get.call_count == 1

    @mock.patch('mwclient.client.Site')
    def test_list_max_items_continuation(self, mock_site):
        # Test that max_items and api_chunk_size work together

        mock_site.api_limit = 500
        lst = List(mock_site, 'allpages', 'ap', max_items=2, api_chunk_size=1)
        self.setupDummyResponsesOne(mock_site, 'allpages')
        vals = [x for x in lst]

        assert len(vals) == 2
        assert type(vals[0]) == dict
        assert lst.args["aplimit"] == "1"
        assert mock_site.get.call_count == 2

    @mock.patch('mwclient.client.Site')
    def test_list_with_str_return_value(self, mock_site):
        # Test that the List yields strings when return_values is string

        lst = List(mock_site, 'allpages', 'ap', limit=2, return_values='title')
        self.setupDummyResponsesTwo(mock_site, 'allpages')
        vals = [x for x in lst]

        assert len(vals) == 3
        assert type(vals[0]) == str

    @mock.patch('mwclient.client.Site')
    def test_list_with_tuple_return_value(self, mock_site):
        # Test that the List yields tuples when return_values is tuple

        lst = List(mock_site, 'allpages', 'ap', limit=2,
                   return_values=('title', 'ns'))
        self.setupDummyResponsesTwo(mock_site, 'allpages')
        vals = [x for x in lst]

        assert len(vals) == 3
        assert type(vals[0]) == tuple

    @mock.patch('mwclient.client.Site')
    def test_list_empty(self, mock_site):
        # Test that we handle an empty response from get correctly
        # (stop iterating)

        lst = List(mock_site, 'allpages', 'ap', limit=2,
                   return_values=('title', 'ns'))
        mock_site.get.side_effect = [{}]
        vals = [x for x in lst]

        assert len(vals) == 0

    @mock.patch('mwclient.client.Site')
    def test_generator_list(self, mock_site):
        # Test that the GeneratorList yields Page objects

        mock_site.api_limit = 500
        lst = GeneratorList(mock_site, 'pages', 'p')
        self.setupDummyResponsesTwo(mock_site, 'pages', ns=[0, 6, 14])
        vals = [x for x in lst]

        assert len(vals) == 3
        assert type(vals[0]) == mwclient.page.Page
        assert type(vals[1]) == mwclient.image.Image
        assert type(vals[2]) == mwclient.listing.Category


if __name__ == '__main__':
    unittest.main()
