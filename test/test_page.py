# encoding=utf-8
from __future__ import print_function

import unittest
import pytest
import logging
import requests
import responses
import mock
import mwclient
from mwclient.page import Page
from mwclient.client import Site
from mwclient.listing import Category
from mwclient.errors import APIError, AssertUserFailedError, ProtectedPageError, InvalidPageTitle

try:
    import json
except ImportError:
    import simplejson as json

if __name__ == "__main__":
    print()
    print("Note: Running in stand-alone mode. Consult the README")
    print("      (section 'Contributing') for advice on running tests.")
    print()


class TestPage(unittest.TestCase):

    def setUp(self):
        pass

    @mock.patch('mwclient.client.Site')
    def test_api_call_on_page_init(self, mock_site):
        # Check that site.get() is called once on Page init

        title = 'Some page'
        mock_site.get.return_value = {
            'query': {'pages': {'1': {}}}
        }
        page = Page(mock_site, title)

        # test that Page called site.get with the right parameters
        mock_site.get.assert_called_once_with('query', inprop='protection', titles=title, prop='info')

    @mock.patch('mwclient.client.Site')
    def test_nonexisting_page(self, mock_site):
        # Check that API response results in page.exists being set to False

        title = 'Some nonexisting page'
        mock_site.get.return_value = {
            'query': {'pages': {'-1': {'missing': ''}}}
        }
        page = Page(mock_site, title)

        assert page.exists is False

    @mock.patch('mwclient.client.Site')
    def test_existing_page(self, mock_site):
        # Check that API response results in page.exists being set to True

        title = 'Norge'
        mock_site.get.return_value = {
            'query': {'pages': {'728': {}}}
        }
        page = Page(mock_site, title)

        assert page.exists is True

    @mock.patch('mwclient.client.Site')
    def test_invalid_title(self, mock_site):
        # Check that API page.exists is False for invalid title

        title = '[Test]'
        mock_site.get.return_value = {
            "query": {
                "pages": {
                    "-1": {
                        "title": "[Test]",
                        "invalidreason": "The requested page title contains invalid characters: \"[\".",
                        "invalid": ""
                    }
                }
            }
        }
        with pytest.raises(InvalidPageTitle):
            page = Page(mock_site, title)

    @mock.patch('mwclient.client.Site')
    def test_pageprops(self, mock_site):
        # Check that variouse page props are read correctly from API response

        title = 'Some page'
        mock_site.get.return_value = {
            'query': {
                'pages': {
                    '728': {
                        'contentmodel': 'wikitext',
                        'counter': '',
                        'lastrevid': 13355471,
                        'length': 58487,
                        'ns': 0,
                        'pageid': 728,
                        'pagelanguage': 'nb',
                        'protection': [],
                        'title': title,
                        'touched': '2014-09-14T21:11:52Z'
                    }
                }
            }
        }
        page = Page(mock_site, title)

        assert page.exists is True
        assert page.redirect is False
        assert page.revision == 13355471
        assert page.length == 58487
        assert page.namespace == 0
        assert page.name == title
        assert page.page_title == title

    @mock.patch('mwclient.client.Site')
    def test_protection_levels(self, mock_site):
        # If page is protected, check that protection is parsed correctly

        title = 'Some page'
        mock_site.get.return_value = {
            'query': {
                'pages': {
                    '728': {
                        'protection': [
                            {
                                'expiry': 'infinity',
                                'level': 'autoconfirmed',
                                'type': 'edit'
                            },
                            {
                                'expiry': 'infinity',
                                'level': 'sysop',
                                'type': 'move'
                            }
                        ]
                    }
                }
            }
        }
        mock_site.rights = ['read', 'edit', 'move']

        page = Page(mock_site, title)

        assert page.protection == {'edit': ('autoconfirmed', 'infinity'), 'move': ('sysop', 'infinity')}
        assert page.can('read') is True
        assert page.can('edit') is False  # User does not have 'autoconfirmed' right
        assert page.can('move') is False  # User does not have 'sysop' right

        mock_site.rights = ['read', 'edit', 'move', 'autoconfirmed']

        assert page.can('edit') is True   # User has 'autoconfirmed'  right
        assert page.can('move') is False  # User doesn't have 'sysop'  right

        mock_site.rights = ['read', 'edit', 'move', 'autoconfirmed', 'editprotected']

        assert page.can('edit') is True  # User has 'autoconfirmed'  right
        assert page.can('move') is True  # User has 'sysop' right

    @mock.patch('mwclient.client.Site')
    def test_redirect(self, mock_site):
        # Check that page.redirect is set correctly

        title = 'Some redirect page'
        mock_site.get.return_value = {
            "query": {
                "pages": {
                    "796917": {
                        "contentmodel": "wikitext",
                        "counter": "",
                        "lastrevid": 9342494,
                        "length": 70,
                        "ns": 0,
                        "pageid": 796917,
                        "pagelanguage": "nb",
                        "protection": [],
                        "redirect": "",
                        "title": title,
                        "touched": "2014-08-29T22:25:15Z"
                    }
                }
            }
        }
        page = Page(mock_site, title)

        assert page.exists is True
        assert page.redirect is True

    @mock.patch('mwclient.client.Site')
    def test_captcha(self, mock_site):
        # Check that Captcha results in EditError
        mock_site.blocked = False
        mock_site.rights = ['read', 'edit']

        title = 'Norge'
        mock_site.get.return_value = {
            'query': {'pages': {'728': {'protection': []}}}
        }
        page = Page(mock_site, title)
        mock_site.post.return_value = {
            'edit': {'result': 'Failure', 'captcha': {
                'type': 'math',
                'mime': 'text/tex',
                'id': '509895952',
                'question': '36 + 4 = '
            }}
        }

        # For now, mwclient will just raise an EditError.
        # <https://github.com/mwclient/mwclient/issues/33>
        with pytest.raises(mwclient.errors.EditError):
            page.save('Some text')


class TestPageApiArgs(unittest.TestCase):

    def setUp(self):
        title = 'Some page'
        self.page_text = 'Hello world'

        MockSite = mock.patch('mwclient.client.Site').start()
        self.site = MockSite()

        self.site.get.return_value = {'query': {'pages': {'1': {'title': title}}}}
        self.site.rights = ['read']
        self.site.api_limit = 500

        self.page = Page(self.site, title)

        self.site.get.return_value = {'query': {'pages': {'2': {
            'ns': 0, 'pageid': 2, 'revisions': [{'*': 'Hello world', 'timestamp': '2014-08-29T22:25:15Z'}], 'title': title
        }}}}

    def get_last_api_call_args(self, http_method='POST'):
        if http_method == 'GET':
            args, kwargs = self.site.get.call_args
        else:
            args, kwargs = self.site.post.call_args
        action = args[0]
        args = args[1:]
        kwargs.update(args)
        return kwargs

    def tearDown(self):
        mock.patch.stopall()

    def test_get_page_text(self):
        # Check that page.text() works, and that a correct API call is made
        text = self.page.text()
        args = self.get_last_api_call_args(http_method='GET')

        assert text == self.page_text
        assert args == {
            'prop': 'revisions',
            'rvdir': 'older',
            'titles': self.page.page_title,
            'rvprop': 'content|timestamp',
            'rvlimit': '1'
        }

    def test_get_page_text_cached(self):
        # Check page.text() caching
        self.page.revisions = mock.Mock(return_value=iter([]))
        self.page.text()
        self.page.text()
        # When cache is hit, revisions is not, so call_count should be 1
        assert self.page.revisions.call_count == 1
        self.page.text(cache=False)
        # With cache explicitly disabled, we should hit revisions
        assert self.page.revisions.call_count == 2

    def test_get_section_text(self):
        # Check that the 'rvsection' parameter is sent to the API
        text = self.page.text(section=0)
        args = self.get_last_api_call_args(http_method='GET')

        assert args['rvsection'] == '0'

    def test_get_text_expanded(self):
        # Check that the 'rvexpandtemplates' parameter is sent to the API
        text = self.page.text(expandtemplates=True)
        args = self.get_last_api_call_args(http_method='GET')

        assert args['rvexpandtemplates'] == '1'

    def test_assertuser_true(self):
        # Check that assert=user is sent when force_login=True
        self.site.blocked = False
        self.site.rights = ['read', 'edit']
        self.site.logged_in = True
        self.site.force_login = True

        self.site.api.return_value = {
            'edit': {'result': 'Ok'}
        }
        self.page.save('Some text')
        args = self.get_last_api_call_args()

        assert args['assert'] == 'user'

    def test_assertuser_false(self):
        # Check that assert=user is not sent when force_login=False
        self.site.blocked = False
        self.site.rights = ['read', 'edit']
        self.site.logged_in = False
        self.site.force_login = False

        self.site.api.return_value = {
            'edit': {'result': 'Ok'}
        }
        self.page.save('Some text')
        args = self.get_last_api_call_args()

        assert 'assert' not in args

    def test_handle_edit_error_assertuserfailed(self):
        # Check that AssertUserFailedError is triggered
        api_error = APIError('assertuserfailed',
                             'Assertion that the user is logged in failed',
                             'See https://en.wikipedia.org/w/api.php for API usage')

        with pytest.raises(AssertUserFailedError):
            self.page.handle_edit_error(api_error, 'n/a')

    def test_handle_edit_error_protected(self):
        # Check that ProtectedPageError is triggered
        api_error = APIError('protectedpage',
                             'The "editprotected" right is required to edit this page',
                             'See https://en.wikipedia.org/w/api.php for API usage')

        with pytest.raises(ProtectedPageError) as pp_error:
            self.page.handle_edit_error(api_error, 'n/a')

        assert pp_error.value.code == 'protectedpage'
        assert str(pp_error.value) == 'The "editprotected" right is required to edit this page'

    def test_get_page_categories(self):
        # Check that page.categories() works, and that a correct API call is made

        self.site.get.return_value = {
            "batchcomplete": "",
            "query": {
                "pages": {
                    "1009371": {
                        "pageid": 1009371,
                        "ns": 14,
                        "title": "Category:1879 births",
                    },
                    "1005547": {
                        "pageid": 1005547,
                        "ns": 14,
                        "title": "Category:1955 deaths",
                    }
                }
            }
        }

        cats = list(self.page.categories())
        args = self.get_last_api_call_args(http_method='GET')

        assert {
            'generator': 'categories',
            'titles': self.page.page_title,
            'iiprop': 'timestamp|user|comment|url|size|sha1|metadata|archivename',
            'inprop': 'protection',
            'prop': 'info|imageinfo',
            'gcllimit': repr(self.page.site.api_limit),
        } == args

        assert set([c.name for c in cats]) == set([
            'Category:1879 births',
            'Category:1955 deaths',
        ])


if __name__ == '__main__':
    unittest.main()
