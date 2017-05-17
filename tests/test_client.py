# encoding=utf-8
from __future__ import print_function

from six import StringIO
import unittest
import pytest
import mwclient
import logging
import requests
import responses
import pkg_resources  # part of setuptools
import mock
import time
from requests_oauthlib import OAuth1

try:
    import json
except ImportError:
    import simplejson as json

if __name__ == "__main__":
    print()
    print("Note: Running in stand-alone mode. Consult the README")
    print("      (section 'Contributing') for advice on running tests.")
    print()

logging.basicConfig(level=logging.DEBUG)


class TestCase(unittest.TestCase):

    def metaResponse(self, **kwargs):
        tpl = '{"query":{"general":{"generator":"MediaWiki %(version)s"},"namespaces":{"-1":{"*":"Special","canonical":"Special","case":"first-letter","id":-1},"-2":{"*":"Media","canonical":"Media","case":"first-letter","id":-2},"0":{"*":"","case":"first-letter","content":"","id":0},"1":{"*":"Talk","canonical":"Talk","case":"first-letter","id":1,"subpages":""},"10":{"*":"Template","canonical":"Template","case":"first-letter","id":10,"subpages":""},"100":{"*":"Test namespace 1","canonical":"Test namespace 1","case":"first-letter","id":100,"subpages":""},"101":{"*":"Test namespace 1 talk","canonical":"Test namespace 1 talk","case":"first-letter","id":101,"subpages":""},"102":{"*":"Test namespace 2","canonical":"Test namespace 2","case":"first-letter","id":102,"subpages":""},"103":{"*":"Test namespace 2 talk","canonical":"Test namespace 2 talk","case":"first-letter","id":103,"subpages":""},"11":{"*":"Template talk","canonical":"Template talk","case":"first-letter","id":11,"subpages":""},"1198":{"*":"Translations","canonical":"Translations","case":"first-letter","id":1198,"subpages":""},"1199":{"*":"Translations talk","canonical":"Translations talk","case":"first-letter","id":1199,"subpages":""},"12":{"*":"Help","canonical":"Help","case":"first-letter","id":12,"subpages":""},"13":{"*":"Help talk","canonical":"Help talk","case":"first-letter","id":13,"subpages":""},"14":{"*":"Category","canonical":"Category","case":"first-letter","id":14},"15":{"*":"Category talk","canonical":"Category talk","case":"first-letter","id":15,"subpages":""},"2":{"*":"User","canonical":"User","case":"first-letter","id":2,"subpages":""},"2500":{"*":"VisualEditor","canonical":"VisualEditor","case":"first-letter","id":2500},"2501":{"*":"VisualEditor talk","canonical":"VisualEditor talk","case":"first-letter","id":2501},"2600":{"*":"Topic","canonical":"Topic","case":"first-letter","defaultcontentmodel":"flow-board","id":2600},"3":{"*":"User talk","canonical":"User talk","case":"first-letter","id":3,"subpages":""},"4":{"*":"Wikipedia","canonical":"Project","case":"first-letter","id":4,"subpages":""},"460":{"*":"Campaign","canonical":"Campaign","case":"case-sensitive","defaultcontentmodel":"Campaign","id":460},"461":{"*":"Campaign talk","canonical":"Campaign talk","case":"case-sensitive","id":461},"5":{"*":"Wikipedia talk","canonical":"Project talk","case":"first-letter","id":5,"subpages":""},"6":{"*":"File","canonical":"File","case":"first-letter","id":6},"7":{"*":"File talk","canonical":"File talk","case":"first-letter","id":7,"subpages":""},"710":{"*":"TimedText","canonical":"TimedText","case":"first-letter","id":710},"711":{"*":"TimedText talk","canonical":"TimedText talk","case":"first-letter","id":711},"8":{"*":"MediaWiki","canonical":"MediaWiki","case":"first-letter","id":8,"subpages":""},"828":{"*":"Module","canonical":"Module","case":"first-letter","id":828,"subpages":""},"829":{"*":"Module talk","canonical":"Module talk","case":"first-letter","id":829,"subpages":""},"866":{"*":"CNBanner","canonical":"CNBanner","case":"first-letter","id":866},"867":{"*":"CNBanner talk","canonical":"CNBanner talk","case":"first-letter","id":867,"subpages":""},"9":{"*":"MediaWiki talk","canonical":"MediaWiki talk","case":"first-letter","id":9,"subpages":""},"90":{"*":"Thread","canonical":"Thread","case":"first-letter","id":90},"91":{"*":"Thread talk","canonical":"Thread talk","case":"first-letter","id":91},"92":{"*":"Summary","canonical":"Summary","case":"first-letter","id":92},"93":{"*":"Summary talk","canonical":"Summary talk","case":"first-letter","id":93}},"userinfo":{"anon":"","groups":["*"],"id":0,"name":"127.0.0.1","rights": %(rights)s}}}'
        tpl = tpl % {'version': kwargs.get('version', '1.24wmf17'),
                     'rights': json.dumps(kwargs.get('rights', ["createaccount", "read", "edit", "createpage", "createtalk", "writeapi", "editmyusercss", "editmyuserjs", "viewmywatchlist", "editmywatchlist", "viewmyprivateinfo", "editmyprivateinfo", "editmyoptions", "centralauth-merge", "abusefilter-view", "abusefilter-log", "translate", "vipsscaler-test", "upload"]))
                     }

        res = json.loads(tpl)
        if kwargs.get('writeapi', True):
            res['query']['general']['writeapi'] = ''

        return res

    def metaResponseAsJson(self, **kwargs):
        return json.dumps(self.metaResponse(**kwargs))

    def httpShouldReturn(self, body=None, callback=None, scheme='https', host='test.wikipedia.org', path='/w/',
                         script='api', headers=None, status=200, method='GET'):
        url = '{scheme}://{host}{path}{script}.php'.format(scheme=scheme, host=host, path=path, script=script)
        mock = responses.GET if method == 'GET' else responses.POST
        if body is None:
            responses.add_callback(mock, url, callback=callback)
        else:
            responses.add(mock, url, body=body, content_type='application/json',
                          adding_headers=headers, status=status)

    def stdSetup(self):
        self.httpShouldReturn(self.metaResponseAsJson())
        site = mwclient.Site('test.wikipedia.org')
        responses.reset()
        return site

    def makePageResponse(self, title='Dummy.jpg', **kwargs):
        # Creates a dummy page response

        pageinfo = {
            "contentmodel": "wikitext",
            "lastrevid": 112353797,
            "length": 389,
            "ns": 6,
            "pageid": 738154,
            "pagelanguage": "en",
            "protection": [],
            "title": title,
            "touched": "2014-09-10T20:37:25Z"
        }
        pageinfo.update(**kwargs)

        res = {
            "query": {
                "pages": {
                    "9": pageinfo
                }
            }
        }
        return json.dumps(res)


class TestClient(TestCase):

    def setUp(self):
        pass

    def testVersion(self):
        # The version specified in setup.py should equal the one specified in client.py
        version = pkg_resources.require("mwclient")[0].version

        assert version == mwclient.__ver__

    @responses.activate
    def test_https_as_default(self):
        # 'https' should be the default scheme

        self.httpShouldReturn(self.metaResponseAsJson(), scheme='https')

        site = mwclient.Site('test.wikipedia.org')

        assert len(responses.calls) == 1
        assert responses.calls[0].request.method == 'GET'

    @responses.activate
    def test_max_lag(self):
        # Client should wait and retry if lag exceeds max-lag

        def request_callback(request):
            if len(responses.calls) == 0:
                return (200, {'x-database-lag': '0', 'retry-after': '0'}, '')
            else:
                return (200, {}, self.metaResponseAsJson())

        self.httpShouldReturn(callback=request_callback, scheme='https')

        site = mwclient.Site('test.wikipedia.org')

        assert len(responses.calls) == 2
        assert 'retry-after' in responses.calls[0].response.headers
        assert 'retry-after' not in responses.calls[1].response.headers

    @responses.activate
    def test_http_error(self):
        # Client should raise HTTPError

        self.httpShouldReturn('Uh oh', scheme='https', status=400)

        with pytest.raises(requests.exceptions.HTTPError):
            site = mwclient.Site('test.wikipedia.org')

    @responses.activate
    def test_force_http(self):
        # Setting http should work

        self.httpShouldReturn(self.metaResponseAsJson(), scheme='http')

        site = mwclient.Site(('http', 'test.wikipedia.org'))

        assert len(responses.calls) == 1

    @responses.activate
    def test_user_agent_is_sent(self):
        # User specified user agent should be sent sent to server

        self.httpShouldReturn(self.metaResponseAsJson())

        site = mwclient.Site('test.wikipedia.org', clients_useragent='MyFabulousClient')

        assert 'MyFabulousClient' in responses.calls[0].request.headers['user-agent']

    @responses.activate
    def test_custom_headers_are_sent(self):
        # Custom headers should be sent to the server

        self.httpShouldReturn(self.metaResponseAsJson())

        site = mwclient.Site('test.wikipedia.org', custom_headers={'X-Wikimedia-Debug': 'host=mw1099.eqiad.wmnet; log'})

        assert 'host=mw1099.eqiad.wmnet; log' in responses.calls[0].request.headers['X-Wikimedia-Debug']

    @responses.activate
    def test_basic_request(self):

        self.httpShouldReturn(self.metaResponseAsJson())

        site = mwclient.Site('test.wikipedia.org')

        assert 'action=query' in responses.calls[0].request.url
        assert 'meta=siteinfo%7Cuserinfo' in responses.calls[0].request.url

    @responses.activate
    def test_httpauth_defaults_to_basic_auth(self):

        self.httpShouldReturn(self.metaResponseAsJson())

        site = mwclient.Site('test.wikipedia.org', httpauth=('me', 'verysecret'))

        assert isinstance(site.connection.auth, requests.auth.HTTPBasicAuth)

    @responses.activate
    def test_httpauth_raise_error_on_invalid_type(self):

        self.httpShouldReturn(self.metaResponseAsJson())

        with pytest.raises(RuntimeError):
            site = mwclient.Site('test.wikipedia.org', httpauth=1)

    @responses.activate
    def test_oauth(self):

        self.httpShouldReturn(self.metaResponseAsJson())

        site = mwclient.Site('test.wikipedia.org',
                             consumer_token='a', consumer_secret='b',
                             access_token='c', access_secret='d')
        assert isinstance(site.connection.auth, OAuth1)

    @responses.activate
    def test_api_disabled(self):
        # Should raise APIDisabledError if API is not enabled

        self.httpShouldReturn('MediaWiki API is not enabled for this site.')

        with pytest.raises(mwclient.errors.APIDisabledError):
            site = mwclient.Site('test.wikipedia.org')

    @responses.activate
    def test_version(self):
        # Should parse the MediaWiki version number correctly

        self.httpShouldReturn(self.metaResponseAsJson(version='1.16'))

        site = mwclient.Site('test.wikipedia.org')

        assert site.initialized is True
        assert site.version == (1, 16)

    @responses.activate
    def test_min_version(self):
        # Should raise MediaWikiVersionError if API version is < 1.16

        self.httpShouldReturn(self.metaResponseAsJson(version='1.15'))

        with pytest.raises(mwclient.errors.MediaWikiVersionError):
            site = mwclient.Site('test.wikipedia.org')

    @responses.activate
    def test_private_wiki(self):
        # Should not raise error

        self.httpShouldReturn(json.dumps({
            'error': {
                'code': 'readapidenied',
                'info': 'You need read permission to use this module'
            }
        }))

        site = mwclient.Site('test.wikipedia.org')

        assert site.initialized is False

    # ----- Use standard setup for rest

    @responses.activate
    def test_headers(self):
        # Content-type should be 'application/x-www-form-urlencoded' for POST requests

        site = self.stdSetup()

        self.httpShouldReturn('{}', method='POST')
        site.post('purge', title='Main Page')

        assert len(responses.calls) == 1
        assert 'content-type' in responses.calls[0].request.headers
        assert responses.calls[0].request.headers['content-type'] == 'application/x-www-form-urlencoded'

    @responses.activate
    def test_raw_index(self):
        # Initializing the client should result in one request

        site = self.stdSetup()

        self.httpShouldReturn('Some data', script='index')
        site.raw_index(action='purge', title='Main Page', http_method='GET')

        assert len(responses.calls) == 1

    @responses.activate
    def test_api_error_response(self):
        # Test that APIError is thrown on error response

        site = self.stdSetup()

        self.httpShouldReturn(json.dumps({
            'error': {
                'code': 'assertuserfailed',
                'info': 'Assertion that the user is logged in failed',
                '*': 'See https://en.wikipedia.org/w/api.php for API usage'
            }
        }), method='POST')
        with pytest.raises(mwclient.errors.APIError) as excinfo:
            site.api(action='edit', title='Wikipedia:Sandbox')

        assert excinfo.value.code == 'assertuserfailed'
        assert excinfo.value.info == 'Assertion that the user is logged in failed'
        assert len(responses.calls) == 1

    @responses.activate
    def test_smw_error_response(self):
        # Test that APIError is thrown on error response from SMW

        site = self.stdSetup()
        self.httpShouldReturn(json.dumps({
            'error': {
                'query': u'Certains « <nowiki>[[</nowiki> » dans votre requête n’ont pas été clos par des « ]] » correspondants.'
            }
        }), method='GET')
        with pytest.raises(mwclient.errors.APIError) as excinfo:
            list(site.ask('test'))

        assert excinfo.value.code is None
        assert excinfo.value.info == u'Certains « <nowiki>[[</nowiki> » dans votre requête n’ont pas été clos par des « ]] » correspondants.'
        assert len(responses.calls) == 1

    @responses.activate
    def test_repr(self):
        # Test repr()

        site = self.stdSetup()

        assert repr(site) == '<Site object \'test.wikipedia.org/w/\'>'


class TestLogin(TestCase):

    @mock.patch('mwclient.client.Site.site_init')
    @mock.patch('mwclient.client.Site.raw_api')
    def test_old_login_flow(self, raw_api, site_init):
        # The login flow used before MW 1.27 that starts with a action=login POST request
        login_token = 'abc+\\'

        def side_effect(*args, **kwargs):

            if 'lgtoken' not in kwargs:
                return {
                    'login': {'result': 'NeedToken', 'token': login_token}
                }
            elif 'lgname' in kwargs:
                assert kwargs['lgtoken'] == login_token
                return {
                    'login': {'result': 'Success'}
                }

        raw_api.side_effect = side_effect

        site = mwclient.Site('test.wikipedia.org')
        site.login('myusername', 'mypassword')

        call_args = raw_api.call_args_list

        assert len(call_args) == 3
        assert call_args[0] == mock.call('query', 'GET', meta='tokens', type='login')
        assert call_args[1] == mock.call('login', 'POST', lgname='myusername', lgpassword='mypassword')
        assert call_args[2] == mock.call('login', 'POST', lgname='myusername', lgpassword='mypassword', lgtoken=login_token)

    @mock.patch('mwclient.client.Site.site_init')
    @mock.patch('mwclient.client.Site.raw_api')
    def test_new_login_flow(self, raw_api, site_init):
        # The login flow used from MW 1.27 that starts with a meta=tokens GET request

        login_token = 'abc+\\'

        def side_effect(*args, **kwargs):
            if kwargs.get('meta') == 'tokens':
                return {
                    'query': {'tokens': {'logintoken': login_token}}
                }
            elif 'lgname' in kwargs:
                assert kwargs['lgtoken'] == login_token
                return {
                    'login': {'result': 'Success'}
                }

        raw_api.side_effect = side_effect

        site = mwclient.Site('test.wikipedia.org')
        site.login('myusername', 'mypassword')

        call_args = raw_api.call_args_list

        assert len(call_args) == 2
        assert call_args[0] == mock.call('query', 'GET', meta='tokens', type='login')
        assert call_args[1] == mock.call('login', 'POST', lgname='myusername', lgpassword='mypassword', lgtoken=login_token)


class TestClientApiMethods(TestCase):

    def setUp(self):
        self.api = mock.patch('mwclient.client.Site.api').start()
        self.api.return_value = self.metaResponse()
        self.site = mwclient.Site('test.wikipedia.org')

    def tearDown(self):
        mock.patch.stopall()

    def test_revisions(self):

        self.api.return_value = {
            'query': {'pages': {'1': {
                'pageid': 1,
                'title': 'Test page',
                'revisions': [{
                    'revid': 689697696,
                    'timestamp': '2015-11-08T21:52:46Z',
                    'comment': 'Test comment 1'
                }, {
                    'revid': 689816909,
                    'timestamp': '2015-11-09T16:09:28Z',
                    'comment': 'Test comment 2'
                }]
            }}}}

        revisions = [rev for rev in self.site.revisions([689697696, 689816909], prop='content')]

        args, kwargs = self.api.call_args
        assert kwargs.get('revids') == '689697696|689816909'
        assert len(revisions) == 2
        assert revisions[0]['pageid'] == 1
        assert revisions[0]['pagetitle'] == 'Test page'
        assert revisions[0]['revid'] == 689697696
        assert revisions[0]['timestamp'] == time.strptime('2015-11-08T21:52:46Z', '%Y-%m-%dT%H:%M:%SZ')
        assert revisions[1]['revid'] == 689816909


class TestClientUploadArgs(TestCase):

    def setUp(self):
        self.raw_call = mock.patch('mwclient.client.Site.raw_call').start()

    def configure(self, rights=['read', 'upload']):

        self.raw_call.side_effect = [self.metaResponseAsJson(rights=rights)]
        self.site = mwclient.Site('test.wikipedia.org')

        self.vars = {
            'fname': u'Some "ßeta" æøå.jpg',
            'comment': u'Some slightly complex comment<br> π ≈ 3, © Me.jpg',
            'token': u'abc+\\'
        }

        self.raw_call.side_effect = [

            # 1st response:
            self.makePageResponse(title='File:Test.jpg', imagerepository='local', imageinfo=[{
                "comment": "",
                "height": 1440,
                "metadata": [],
                "sha1": "69a764a9cf8307ea4130831a0aa0b9b7f9585726",
                "size": 123,
                "timestamp": "2013-12-22T07:11:07Z",
                "user": "TestUser",
                "width": 2160
            }]),

            # 2nd response:
            json.dumps({'query': {'tokens': {'csrftoken': self.vars['token']}}}),

            # 3rd response:
            json.dumps({
                "upload": {
                    "result": "Success",
                    "filename": self.vars['fname'],
                    "imageinfo": []
                }
            })
        ]

    def tearDown(self):
        mock.patch.stopall()

    def test_upload_args(self):
        # Test that methods are called, and arguments sent as expected
        self.configure()

        self.site.upload(file=StringIO('test'), filename=self.vars['fname'], comment=self.vars['comment'])

        args, kwargs = self.raw_call.call_args
        data = args[1]
        files = args[2]

        assert data.get('action') == 'upload'
        assert data.get('filename') == self.vars['fname']
        assert data.get('comment') == self.vars['comment']
        assert data.get('token') == self.vars['token']
        assert 'file' in files

    def test_upload_missing_filename(self):
        self.configure()

        with pytest.raises(TypeError):
            self.site.upload(file=StringIO('test'))

    def test_upload_ambigitious_args(self):
        self.configure()

        with pytest.raises(TypeError):
            self.site.upload(filename='Test', file=StringIO('test'), filekey='abc')

    def test_upload_missing_upload_permission(self):
        self.configure(rights=['read'])

        with pytest.raises(mwclient.errors.InsufficientPermission):
            self.site.upload(filename='Test', file=StringIO('test'))


class TestClientGetTokens(TestCase):

    def setUp(self):
        self.raw_call = mock.patch('mwclient.client.Site.raw_call').start()

    def configure(self, version='1.24'):
        self.raw_call.return_value = self.metaResponseAsJson(version=version)
        self.site = mwclient.Site('test.wikipedia.org')
        responses.reset()

    def tearDown(self):
        mock.patch.stopall()

    def test_token_new_system(self):
        # Test get_token for MW >= 1.24
        self.configure(version='1.24')

        self.raw_call.return_value = json.dumps({
            'query': {'tokens': {'csrftoken': 'sometoken'}}
        })
        self.site.get_token('edit')

        args, kwargs = self.raw_call.call_args
        data = args[1]

        assert 'intoken' not in data
        assert data.get('type') == 'csrf'
        assert 'csrf' in self.site.tokens
        assert self.site.tokens['csrf'] == 'sometoken'
        assert 'edit' not in self.site.tokens

    def test_token_old_system_without_specifying_title(self):
        # Test get_token for MW < 1.24
        self.configure(version='1.23')

        self.raw_call.return_value = self.makePageResponse(edittoken='sometoken', title='Test')
        self.site.get_token('edit')

        args, kwargs = self.raw_call.call_args
        data = args[1]

        assert 'type' not in data
        assert data.get('intoken') == 'edit'
        assert 'edit' in self.site.tokens
        assert self.site.tokens['edit'] == 'sometoken'
        assert 'csrf' not in self.site.tokens

    def test_token_old_system_with_specifying_title(self):
        # Test get_token for MW < 1.24
        self.configure(version='1.23')

        self.raw_call.return_value = self.makePageResponse(edittoken='sometoken', title='Some page')
        self.site.get_token('edit', title='Some page')

        args, kwargs = self.raw_call.call_args
        data = args[1]

        assert self.site.tokens['edit'] == 'sometoken'

if __name__ == '__main__':
    unittest.main()
