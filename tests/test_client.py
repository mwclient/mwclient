# encoding=utf-8

if __name__ == "__main__":
    print
    print "Note: Running in stand-alone mode. Consult the README"
    print "      (section 'Contributing') for advice on running tests."
    print

import unittest
import pytest
import mwclient
import logging
import requests
import responses
import pkg_resources  # part of setuptools

try:
    import json
except ImportError:
    import simplejson as json


class TestCase(unittest.TestCase):

    def makeMetaResponse(self, **kwargs):
        tpl = '{"query":{"general":{"generator":"MediaWiki %(version)s"},"namespaces":{"-1":{"*":"Special","canonical":"Special","case":"first-letter","id":-1},"-2":{"*":"Media","canonical":"Media","case":"first-letter","id":-2},"0":{"*":"","case":"first-letter","content":"","id":0},"1":{"*":"Talk","canonical":"Talk","case":"first-letter","id":1,"subpages":""},"10":{"*":"Template","canonical":"Template","case":"first-letter","id":10,"subpages":""},"100":{"*":"Test namespace 1","canonical":"Test namespace 1","case":"first-letter","id":100,"subpages":""},"101":{"*":"Test namespace 1 talk","canonical":"Test namespace 1 talk","case":"first-letter","id":101,"subpages":""},"102":{"*":"Test namespace 2","canonical":"Test namespace 2","case":"first-letter","id":102,"subpages":""},"103":{"*":"Test namespace 2 talk","canonical":"Test namespace 2 talk","case":"first-letter","id":103,"subpages":""},"11":{"*":"Template talk","canonical":"Template talk","case":"first-letter","id":11,"subpages":""},"1198":{"*":"Translations","canonical":"Translations","case":"first-letter","id":1198,"subpages":""},"1199":{"*":"Translations talk","canonical":"Translations talk","case":"first-letter","id":1199,"subpages":""},"12":{"*":"Help","canonical":"Help","case":"first-letter","id":12,"subpages":""},"13":{"*":"Help talk","canonical":"Help talk","case":"first-letter","id":13,"subpages":""},"14":{"*":"Category","canonical":"Category","case":"first-letter","id":14},"15":{"*":"Category talk","canonical":"Category talk","case":"first-letter","id":15,"subpages":""},"2":{"*":"User","canonical":"User","case":"first-letter","id":2,"subpages":""},"2500":{"*":"VisualEditor","canonical":"VisualEditor","case":"first-letter","id":2500},"2501":{"*":"VisualEditor talk","canonical":"VisualEditor talk","case":"first-letter","id":2501},"2600":{"*":"Topic","canonical":"Topic","case":"first-letter","defaultcontentmodel":"flow-board","id":2600},"3":{"*":"User talk","canonical":"User talk","case":"first-letter","id":3,"subpages":""},"4":{"*":"Wikipedia","canonical":"Project","case":"first-letter","id":4,"subpages":""},"460":{"*":"Campaign","canonical":"Campaign","case":"case-sensitive","defaultcontentmodel":"Campaign","id":460},"461":{"*":"Campaign talk","canonical":"Campaign talk","case":"case-sensitive","id":461},"5":{"*":"Wikipedia talk","canonical":"Project talk","case":"first-letter","id":5,"subpages":""},"6":{"*":"File","canonical":"File","case":"first-letter","id":6},"7":{"*":"File talk","canonical":"File talk","case":"first-letter","id":7,"subpages":""},"710":{"*":"TimedText","canonical":"TimedText","case":"first-letter","id":710},"711":{"*":"TimedText talk","canonical":"TimedText talk","case":"first-letter","id":711},"8":{"*":"MediaWiki","canonical":"MediaWiki","case":"first-letter","id":8,"subpages":""},"828":{"*":"Module","canonical":"Module","case":"first-letter","id":828,"subpages":""},"829":{"*":"Module talk","canonical":"Module talk","case":"first-letter","id":829,"subpages":""},"866":{"*":"CNBanner","canonical":"CNBanner","case":"first-letter","id":866},"867":{"*":"CNBanner talk","canonical":"CNBanner talk","case":"first-letter","id":867,"subpages":""},"9":{"*":"MediaWiki talk","canonical":"MediaWiki talk","case":"first-letter","id":9,"subpages":""},"90":{"*":"Thread","canonical":"Thread","case":"first-letter","id":90},"91":{"*":"Thread talk","canonical":"Thread talk","case":"first-letter","id":91},"92":{"*":"Summary","canonical":"Summary","case":"first-letter","id":92},"93":{"*":"Summary talk","canonical":"Summary talk","case":"first-letter","id":93}},"userinfo":{"anon":"","groups":["*"],"id":0,"name":"127.0.0.1","rights": %(rights)s}}}'
        tpl = tpl % {'version': kwargs.get('version', '1.24wmf17'),
                     'rights': json.dumps(kwargs.get('rights', ["createaccount", "read", "edit", "createpage", "createtalk", "writeapi", "editmyusercss", "editmyuserjs", "viewmywatchlist", "editmywatchlist", "viewmyprivateinfo", "editmyprivateinfo", "editmyoptions", "centralauth-merge", "abusefilter-view", "abusefilter-log", "translate", "vipsscaler-test", "upload"]))
                     }

        res = json.loads(tpl)
        if kwargs.get('writeapi', True):
            res['query']['general']['writeapi'] = ''

        return json.dumps(res)

    def httpShouldReturn(self, body=None, callback=None, scheme='http', host='test.wikipedia.org', path='/w/',
                         script='api'):
        url = '{scheme}://{host}{path}{script}.php'.format(scheme=scheme, host=host, path=path, script=script)
        if body is None:
            responses.add_callback(responses.POST, url, callback=callback, content_type='application/json')
        else:
            responses.add(responses.POST, url, body=body, content_type='application/json')

    def stdSetup(self):
        self.httpShouldReturn(self.makeMetaResponse())
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
    def test_http_as_default(self):
        # 'http' should be the default scheme (for historical reasons)

        self.httpShouldReturn(self.makeMetaResponse(), scheme='http')

        site = mwclient.Site('test.wikipedia.org')

        assert len(responses.calls) == 1
        assert responses.calls[0].request.method == 'POST'

    @responses.activate
    def test_headers(self):
        # Content-type should be 'application/x-www-form-urlencoded'

        self.httpShouldReturn(self.makeMetaResponse(), scheme='http')

        site = mwclient.Site('test.wikipedia.org')

        assert len(responses.calls) == 1
        assert 'content-type' in responses.calls[0].request.headers
        assert responses.calls[0].request.headers['content-type'] == 'application/x-www-form-urlencoded'

    @responses.activate
    def test_force_https(self):
        # Setting https should work

        self.httpShouldReturn(self.makeMetaResponse(), scheme='https')

        site = mwclient.Site(('https', 'test.wikipedia.org'))

        assert len(responses.calls) == 1

    @responses.activate
    def test_user_agent_is_sent(self):
        # User specified user agent should be sent sent to server

        self.httpShouldReturn(self.makeMetaResponse())

        site = mwclient.Site('test.wikipedia.org', clients_useragent='MyFabulousClient')

        assert 'MyFabulousClient' in responses.calls[0].request.headers['user-agent']

    @responses.activate
    def test_basic_request(self):

        self.httpShouldReturn(self.makeMetaResponse())

        site = mwclient.Site('test.wikipedia.org')

        assert 'action=query' in responses.calls[0].request.body
        assert 'meta=siteinfo%7Cuserinfo' in responses.calls[0].request.body

    @responses.activate
    def test_api_disabled(self):
        # Should raise APIDisabledError if API is not enabled

        self.httpShouldReturn('MediaWiki API is not enabled for this site.')

        with pytest.raises(mwclient.errors.APIDisabledError):
            site = mwclient.Site('test.wikipedia.org')

    @responses.activate
    def test_version(self):
        # Should parse the MediaWiki version number correctly

        self.httpShouldReturn(self.makeMetaResponse(version='1.16'))

        site = mwclient.Site('test.wikipedia.org')

        assert site.initialized is True
        assert site.version == (1, 16)

    @responses.activate
    def test_min_version(self):
        # Should raise MediaWikiVersionError if API version is < 1.16

        self.httpShouldReturn(self.makeMetaResponse(version='1.15'))

        with pytest.raises(mwclient.errors.MediaWikiVersionError):
            site = mwclient.Site('test.wikipedia.org')

    # ----- Use standard setup for rest

    @responses.activate
    def test_raw_index(self):
        # Initializing the client should result in one request

        site = self.stdSetup()

        self.httpShouldReturn('Some data', script='index')
        site.raw_index(action='purge', title='Main Page')

        assert len(responses.calls) == 1


if __name__ == '__main__':
    unittest.main()
