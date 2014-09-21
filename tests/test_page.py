# encoding=utf-8

if __name__ == "__main__":
    print
    print "Note: Running in stand-alone mode. Consult the README"
    print "      (section 'Contributing') for advice on running tests."
    print

import unittest
import pytest
import logging
import requests
import responses
import mock
from mwclient.page import Page

try:
    import json
except ImportError:
    import simplejson as json


class TestPage(unittest.TestCase):

    def setUp(self):
        pass

    @mock.patch('mwclient.client.Site')
    def test_api_call_on_page_init(self, mock_site):
        # Check that site.api() is called once on Page init

        title = 'Some page'
        mock_site.api.return_value = {
            'query': {'pages': {'1': {}}}
        }
        page = Page(mock_site, title)

        # test that Page called site.api with the right parameters
        mock_site.api.assert_called_once_with('query', inprop='protection', titles=title, prop='info')

    @mock.patch('mwclient.client.Site')
    def test_nonexisting_page(self, mock_site):
        # Check that API response results in page.exists being set to False

        title = 'Some nonexisting page'
        mock_site.api.return_value = {
            'query': {'pages': {'-1': {'missing': ''}}}
        }
        page = Page(mock_site, title)

        assert page.exists is False

    @mock.patch('mwclient.client.Site')
    def test_existing_page(self, mock_site):
        # Check that API response results in page.exists being set to True

        title = 'Norge'
        mock_site.api.return_value = {
            'query': {'pages': {'728': {}}}
        }
        page = Page(mock_site, title)

        assert page.exists is True

    @mock.patch('mwclient.client.Site')
    def test_pageprops(self, mock_site):
        # Check that variouse page props are read correctly from API response

        title = 'Some page'
        mock_site.api.return_value = {
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
    def test_proection_levels(self, mock_site):
        # If page is protected, check that protection is parsed correctly

        title = 'Some page'
        mock_site.api.return_value = {
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
        mock_site.api.return_value = {
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
    def test_page_get_text(self, mock_site):
        # Check that page.text() works, and that a correct API call is made

        title = 'Some page'
        some_text = 'Hello world'
        mock_site.api.return_value = {'query': {'pages': {'1': {'title': title}}}}
        mock_site.rights = ['read']

        page = Page(mock_site, title)

        mock_site.api.return_value = {
            'query': {
                'pages': {
                    '796917': {
                        'ns': 0,
                        'pageid': 796917,
                        'revisions': [
                            {
                                '*': some_text,
                                'contentformat': 'text/x-wiki',
                                'contentmodel': 'wikitext',
                                'timestamp': '2011-09-12T12:36:08Z'
                            }
                        ],
                        'title': title
                    }
                }
            }
        }

        text = page.text()

        # test that Page called site.api with the right parameters
        mock_site.api.assert_called_with('query', ('prop', 'revisions'), ('rvdir', 'older'), ('titles', title), ('rvprop', 'content|timestamp'), ('rvlimit', '1'))

        assert text == some_text

    @mock.patch('mwclient.client.Site')
    def test_section_get_text(self, mock_site):
        # Check that the 'rvsection' parameter is sent to the API

        title = 'Some page'
        some_text = 'Hello world'
        mock_site.api.return_value = {'query': {'pages': {'1': {'title': title}}}}
        mock_site.rights = ['read']

        page = Page(mock_site, title)

        mock_site.api.return_value = {
            'query': {
                'pages': {
                    '796917': {
                        'ns': 0,
                        'pageid': 796917,
                        'revisions': [
                            {
                                '*': some_text,
                                'contentformat': 'text/x-wiki',
                                'contentmodel': 'wikitext',
                                'timestamp': '2011-09-12T12:36:08Z'
                            }
                        ],
                        'title': title
                    }
                }
            }
        }

        text = page.text(section=0)

        # test that Page called site.api with the right parameters
        mock_site.api.assert_called_with('query', ('prop', 'revisions'), ('rvdir', 'older'), ('titles', title), ('rvsection', '0'), ('rvprop', 'content|timestamp'), ('rvlimit', '1'))


if __name__ == '__main__':
    unittest.main()
