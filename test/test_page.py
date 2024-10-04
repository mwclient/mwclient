import time
import unittest
import unittest.mock as mock

import pytest

import mwclient
from mwclient.errors import APIError, AssertUserFailedError, ProtectedPageError, \
    InvalidPageTitle
from mwclient.page import Page

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

        # check an unusual case: no 'expiry' key, see
        # https://github.com/mwclient/mwclient/issues/290
        del mock_site.get.return_value['query']['pages']['728']['protection'][0]['expiry']
        page = Page(mock_site, title)
        assert page.protection == {'edit': ('autoconfirmed', None), 'move': ('sysop', 'infinity')}

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
            page.edit('Some text')

    @mock.patch('mwclient.client.Site')
    def test_edit(self, mock_site):
        mock_site.blocked = False
        mock_site.rights = ['read', 'edit']
        mock_site.get.return_value = {'query': {'pages': {
            '-1': {'ns': 1, 'title': 'Talk:Some page/Archive 1', 'missing': ''}
        }}}
        page = Page(mock_site, 'Talk:Some page/Archive 1')

        mock_site.post.return_value = {
            'edit': {'result': 'Success', 'pageid': 1234,
                     'title': 'Talk:Some page/Archive 1', 'contentmodel': 'wikitext',
                     'oldrevid': 123456, 'newrevid': 123457,
                     'newtimestamp': '2024-10-02T12:34:07Z'}

        }
        page.edit('Some text')

        mock_site.post.assert_called_once()
        assert page.exists, 'Page should exist after edit'
        assert page.pageid == 1234
        assert page.name == 'Talk:Some page/Archive 1'
        assert page.page_title == 'Some page/Archive 1'
        assert page.base_title == 'Some page'
        assert page.base_name == 'Talk:Some page'
        assert page.contentmodel == 'wikitext'
        assert page.revision == 123457
        assert page.last_rev_time == time.struct_time(
            (2024, 10, 2, 12, 34, 7, 2, 276, -1)
        )
        assert page.touched == time.struct_time(
            (2024, 10, 2, 12, 34, 7, 2, 276, -1)
        )

    @mock.patch('mwclient.client.Site')
    def test_delete(self, mock_site):
        mock_site.rights = ['read', 'delete']
        page_title = 'Some page'
        page = Page(mock_site, page_title, info={
            'contentmodel': 'wikitext',
            'counter': '',
            'lastrevid': 13355471,
            'length': 58487,
            'ns': 0,
            'pageid': 728,
            'pagelanguage': 'nb',
            'protection': [],
            'title': page_title,
            'touched': '2014-09-14T21:11:52Z'
        })

        reason = 'Some reason'
        mock_site.post.return_value = {
            'delete': {'title': page_title, 'reason': reason, 'logid': 1234}
        }
        page.delete(reason)

        mock_site.post.assert_called_once_with(
            'delete', title=page_title, reason=reason, token=mock.ANY
        )
        assert not page.exists, 'Page should not exist after delete'

    @mock.patch('mwclient.client.Site')
    def test_move(self, mock_site):
        mock_site.rights = ['read', 'move']
        page_title = 'Some page'
        page = Page(mock_site, page_title, info={
            'contentmodel': 'wikitext',
            'counter': '',
            'lastrevid': 13355471,
            'length': 58487,
            'ns': 0,
            'pageid': 728,
            'pagelanguage': 'nb',
            'protection': [],
            'title': page_title,
            'touched': '2014-09-14T21:11:52Z'
        })

        new_title = 'Some new page'
        reason = 'Some reason'
        mock_site.post.return_value = {
            'move': {'from': page_title, 'to': new_title, 'reason': reason,
                     'redirectcreated': ''}
        }
        page.move(new_title, reason)

        assert page.exists, 'Page should still exist after move'
        assert page.redirect, 'Page should be a redirect after move'

    @mock.patch('mwclient.client.Site')
    def test_move_no_redirect(self, mock_site):
        mock_site.rights = ['read', 'move']
        page_title = 'Some page'
        page = Page(mock_site, page_title, info={
            'contentmodel': 'wikitext',
            'counter': '',
            'lastrevid': 13355471,
            'length': 58487,
            'ns': 0,
            'pageid': 728,
            'pagelanguage': 'nb',
            'protection': [],
            'title': page_title,
            'touched': '2014-09-14T21:11:52Z'
        })

        new_title = 'Some new page'
        reason = 'Some reason'
        mock_site.post.return_value = {
            'move': {'from': page_title, 'to': new_title, 'reason': reason}
        }
        page.move(new_title, reason, no_redirect=True)

        assert not page.exists, 'Page should not exist after move'
        assert not page.redirect, 'Page should not be a redirect after move'


class TestPageApiArgs(unittest.TestCase):

    def setUp(self):
        title = 'Some page'
        self.page_text = 'Hello world'

        MockSite = mock.patch('mwclient.client.Site').start()
        self.site = MockSite()

        self.site.get.return_value = {'query': {'pages': {'1': {'title': title}}}}
        self.site.rights = ['read']
        self.site.api_limit = 500
        self.site.version = (1, 32, 0)

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
            'uselang': None,
            'rvprop': 'content|timestamp',
            'rvlimit': '1',
            'rvslots': 'main',
        }

    def test_get_page_text_cached(self):
        # Check page.text() caching
        self.page.revisions = mock.Mock(return_value=iter([]))  # type: ignore
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

        assert self.site.expandtemplates.call_count == 1
        assert args.get('rvexpandtemplates') is None

    def test_assertuser_true(self):
        # Check that assert=user is sent when force_login=True
        self.site.blocked = False
        self.site.rights = ['read', 'edit']
        self.site.logged_in = True
        self.site.force_login = True

        self.site.api.return_value = {
            'edit': {'result': 'Ok'}
        }
        self.page.edit('Some text')
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
        self.page.edit('Some text')
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

        assert {c.name for c in cats} == {
            'Category:1879 births',
            'Category:1955 deaths',
        }


if __name__ == '__main__':
    unittest.main()
