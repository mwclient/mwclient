import unittest
import pytest
import mwclient
from mwclient.listing import List, NestedList, GeneratorList, Category, PageList
from mwclient.page import Page

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
    def test_list_invalid(self, mock_site):
        # Test that we handle the response for a list that doesn't
        # exist correctly (set an empty iterator, then stop
        # iterating)

        mock_site.api_limit = 500
        lst = List(mock_site, 'allpagess', 'ap')
        mock_site.get.side_effect = [
            {
                'batchcomplete': '',
                'warnings': {
                    'main': {'*': 'Unrecognized parameter: aplimit.'},
                    'query': {'*': 'Unrecognized value for parameter "list": allpagess'}
                },
                'query': {
                    'userinfo': {
                        'id': 0,
                        'name': 'DEAD:BEEF:CAFE',
                        'anon': ''
                    }
                }
            }
        ]
        vals = [x for x in lst]
        assert len(vals) == 0

    @mock.patch('mwclient.client.Site')
    def test_list_repr(self, mock_site):
        # Test __repr__ of a List is as expected

        mock_site.__str__.return_value = "some wiki"
        lst = List(mock_site, 'allpages', 'ap', limit=2,
                   return_values=('title', 'ns'))
        assert repr(lst) == "<List object 'allpages' for some wiki>"

    @mock.patch('mwclient.client.Site')
    def test_get_list(self, mock_site):
        # Test get_list behaves as expected

        lst = List.get_list()(mock_site, 'allpages', 'ap', limit=2,
                              return_values=('title', 'ns'))
        genlst = List.get_list(True)(mock_site, 'allpages', 'ap', limit=2,
                                     return_values=('title', 'ns'))
        assert isinstance(lst, List)
        assert not isinstance(lst, GeneratorList)
        assert isinstance(genlst, GeneratorList)

    @mock.patch('mwclient.client.Site')
    def test_nested_list(self, mock_site):
        # Test NestedList class works as expected

        mock_site.api_limit = 500
        nested = NestedList('entries', mock_site, 'checkuserlog', 'cul')
        mock_site.get.side_effect = [
            # this is made-up because I do not have permissions on any
            # wiki with this extension installed and the extension doc
            # does not show a sample API response
            {
                'query': {
                    'checkuserlog': {
                        'entries': [
                            {
                                'user': 'Dreamyjazz',
                                'action': 'users',
                                'ip': '172.18.0.1',
                                'message': 'suspected sockpuppet',
                                'time': 1662328680
                            },
                            {
                                'user': 'Dreamyjazz',
                                'action': 'ip',
                                'targetuser': 'JohnDoe124',
                                'message': 'suspected sockpuppet',
                                'time': 1662328380
                            },
                        ]
                    }
                }
            }
        ]
        vals = [x for x in nested]
        assert len(vals) == 2
        assert vals[0]['action'] == 'users'
        assert vals[1]['action'] == 'ip'

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

    @mock.patch('mwclient.client.Site')
    def test_category(self, mock_site):
        # Test that Category works as expected

        mock_site.__str__.return_value = "some wiki"
        mock_site.api_limit = 500
        # first response is for Page.__init__ as Category inherits
        # from both Page and GeneratorList, second response is for
        # the Category treated as an iterator with the namespace
        # filter applied, third response is for the Category.members()
        # call without a namespace filter
        mock_site.get.side_effect = [
            {
                'query': {
                    'pages': {
                        '54565': {
                            'pageid': 54565, 'ns': 14, 'title': 'Category:Furry things'
                        }
                    }
                }
            },
            {
                'query': {
                    'pages': {
                        '36245': {
                            'pageid': 36245,
                            'ns': 118,
                            'title': 'Draft:Cat'
                        },
                        '36275': {
                            'pageid': 36275,
                            'ns': 118,
                            'title': 'Draft:Dog'
                        }
                    }
                }
            },
            {
                'query': {
                    'pages': {
                        '36245': {
                            'pageid': 36245,
                            'ns': 118,
                            'title': 'Draft:Cat'
                        },
                        '36275': {
                            'pageid': 36275,
                            'ns': 118,
                            'title': 'Draft:Dog'
                        },
                        '36295': {
                            'pageid': 36295,
                            'ns': 0,
                            'title': 'Hamster'
                        }
                    }
                }
            },
        ]

        cat = Category(mock_site, 'Category:Furry things', namespace=118)
        assert repr(cat) == "<Category object 'Category:Furry things' for some wiki>"
        assert cat.args['gcmnamespace'] == 118
        vals = [x for x in cat]
        assert len(vals) == 2
        assert vals[0].name == "Draft:Cat"
        newcat = cat.members()
        assert 'gcmnamespace' not in newcat.args
        vals = [x for x in newcat]
        assert len(vals) == 3
        assert vals[2].name == "Hamster"

    @mock.patch('mwclient.client.Site')
    def test_pagelist(self, mock_site):
        # Test that PageList works as expected
        mock_site.__str__.return_value = "some wiki"
        mock_site.api_limit = 500
        mock_site.namespaces = {0: "", 6: "Image", 14: "Category"}
        mock_site.get.return_value = {
            'query': {
                'pages': {
                    '8052484': {
                        'pageid': 8052484, 'ns': 0, 'title': 'Impossible'
                    }
                }
            }
        }
        pl = PageList(mock_site, start="Herring", end="Marmalade")
        assert pl.args["gapfrom"] == "Herring"
        assert pl.args["gapto"] == "Marmalade"
        pg = pl["Impossible"]
        assert isinstance(pg, Page)
        assert mock_site.get.call_args[0] == ("query",)
        assert mock_site.get.call_args[1]["titles"] == "Impossible"
        # covers the catch of AttributeError in get()
        pg = pl[8052484]
        assert isinstance(pg, Page)
        assert mock_site.get.call_args[0] == ("query",)
        assert mock_site.get.call_args[1]["pageids"] == 8052484
        pg = pl["Category:Spreads"]
        assert mock_site.get.call_args[1]["titles"] == "Category:Spreads"
        assert isinstance(pg, Category)
        pl = PageList(mock_site, prefix="Ham")
        assert pl.args["gapprefix"] == "Ham"


if __name__ == '__main__':
    unittest.main()
