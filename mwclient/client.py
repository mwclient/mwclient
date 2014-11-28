__ver__ = '0.7.2dev'

import warnings
import time
import random
import sys
import weakref
import logging
from six import text_type

try:
    # Python 2.7+
    from collections import OrderedDict
except ImportError:
    # Python 2.6
    from ordereddict import OrderedDict

try:
    import json
except ImportError:
    import simplejson as json
import requests
from requests.auth import HTTPBasicAuth, AuthBase

import errors
import listing
import page

try:
    import gzip
except ImportError:
    gzip = None

log = logging.getLogger(__name__)


def parse_timestamp(t):
    if t == '0000-00-00T00:00:00Z':
        return (0, 0, 0, 0, 0, 0, 0, 0)
    return time.strptime(t, '%Y-%m-%dT%H:%M:%SZ')


class WaitToken(object):

    def __init__(self):
        self.id = '%x' % random.randint(0, sys.maxint)

    def __hash__(self):
        return hash(self.id)


class Site(object):
    api_limit = 500

    def __init__(self, host, path='/w/', ext='.php', pool=None, retry_timeout=30,
                 max_retries=25, wait_callback=lambda *x: None, clients_useragent=None,
                 max_lag=3, compress=True, force_login=True, do_init=True, httpauth=None):
        # Setup member variables
        self.host = host
        self.path = path
        self.ext = ext
        self.credentials = None
        self.compress = compress
        self.retry_timeout = retry_timeout
        self.max_retries = max_retries
        self.wait_callback = wait_callback
        self.max_lag = text_type(max_lag)
        self.force_login = force_login

        if isinstance(httpauth, (list, tuple)):
            self.httpauth = HTTPBasicAuth(*httpauth)
        elif httpauth is None or isinstance(httpauth, (AuthBase,)):
            self.httpauth = httpauth
        else:
            raise RuntimeError('Authentication is not a tuple or an instance of AuthBase')

        # The token string => token object mapping
        self.wait_tokens = weakref.WeakKeyDictionary()

        # Site properties
        self.blocked = False    # Whether current user is blocked
        self.hasmsg = False  # Whether current user has new messages
        self.groups = []    # Groups current user belongs to
        self.rights = []    # Rights current user has
        self.tokens = {}    # Edit tokens of the current user
        self.version = None

        self.namespaces = self.default_namespaces
        self.writeapi = False

        # Setup connection
        if pool is None:
            self.connection = requests.Session()
            self.connection.auth = self.httpauth
            self.connection.headers['User-Agent'] = 'MwClient/' + __ver__ + ' (https://github.com/mwclient/mwclient)'
            if clients_useragent:
                self.connection.headers['User-Agent'] = clients_useragent + ' - ' + self.connection.headers['User-Agent']
        else:
            self.connection = pool

        # Page generators
        self.pages = listing.PageList(self)
        self.categories = listing.PageList(self, namespace=14)
        self.images = listing.PageList(self, namespace=6)

        # Compat page generators
        self.Pages = self.pages
        self.Categories = self.categories
        self.Images = self.images

        # Initialization status
        self.initialized = False

        if do_init:
            try:
                self.site_init()
            except errors.APIError as e:
                # Private wiki, do init after login
                if e.args[0] not in (u'unknown_action', u'readapidenied'):
                    raise

    def site_init(self):
        meta = self.api('query', meta='siteinfo|userinfo',
                        siprop='general|namespaces', uiprop='groups|rights')

        # Extract site info
        self.site = meta['query']['general']
        self.namespaces = dict(((i['id'], i.get('*', '')) for i in meta['query']['namespaces'].itervalues()))
        self.writeapi = 'writeapi' in self.site

        # Determine version
        if self.site['generator'].startswith('MediaWiki '):
            version = self.site['generator'][10:].split('.')

            def split_num(s):
                i = 0
                while i < len(s):
                    if s[i] < '0' or s[i] > '9':
                        break
                    i += 1
                if s[i:]:
                    return (int(s[:i]), s[i:], )
                else:
                    return (int(s[:i]), )
            self.version = sum((split_num(s) for s in version), ())

            if len(self.version) < 2:
                raise errors.MediaWikiVersionError('Unknown MediaWiki %s' % '.'.join(version))
        else:
            raise errors.MediaWikiVersionError('Unknown generator %s' % self.site['generator'])

        # Require MediaWiki version >= 1.16
        self.require(1, 16)

        # User info
        userinfo = meta['query']['userinfo']
        self.username = userinfo['name']
        self.groups = userinfo.get('groups', [])
        self.rights = userinfo.get('rights', [])
        self.initialized = True

    default_namespaces = {0: u'', 1: u'Talk', 2: u'User', 3: u'User talk', 4: u'Project', 5: u'Project talk',
                          6: u'Image', 7: u'Image talk', 8: u'MediaWiki', 9: u'MediaWiki talk', 10: u'Template', 11: u'Template talk',
                          12: u'Help', 13: u'Help talk', 14: u'Category', 15: u'Category talk', -1: u'Special', -2: u'Media'}

    def __repr__(self):
        return "<Site object '%s%s'>" % (self.host, self.path)

    def api(self, action, *args, **kwargs):
        """
        Perform a generic API call and handle errors. All arguments will be passed on.

        Example:
            To get coordinates from the GeoData MediaWiki extension at English Wikipedia:

            >>> site = Site('en.wikipedia.org')
            >>> result = site.api('query', prop='coordinates', titles='Oslo|Copenhagen')
            >>> for page in result['query']['pages'].values():
            ...     if 'coordinates' in page:
            ...         print page['title'], page['coordinates'][0]['lat'], page['coordinates'][0]['lon']
            Oslo 59.95 10.75
            Copenhagen 55.6761 12.5683

        Returns:
            The raw response from the API call, as a dictionary.
        """
        kwargs.update(args)

        if 'continue' not in kwargs:
            kwargs['continue'] = ''
        if action == 'query':
            if 'meta' in kwargs:
                kwargs['meta'] += '|userinfo'
            else:
                kwargs['meta'] = 'userinfo'
            if 'uiprop' in kwargs:
                kwargs['uiprop'] += '|blockinfo|hasmsg'
            else:
                kwargs['uiprop'] = 'blockinfo|hasmsg'

        token = self.wait_token()
        while True:
            info = self.raw_api(action, **kwargs)
            if not info:
                info = {}
            res = self.handle_api_result(info, token=token)
            if res:
                return info

    def handle_api_result(self, info, kwargs=None, token=None):
        if token is None:
            token = self.wait_token()

        try:
            userinfo = info['query']['userinfo']
        except KeyError:
            userinfo = ()
        if 'blockedby' in userinfo:
            self.blocked = (userinfo['blockedby'], userinfo.get('blockreason', u''))
        else:
            self.blocked = False
        self.hasmsg = 'message' in userinfo
        self.logged_in = 'anon' not in userinfo
        if 'error' in info:
            if info['error']['code'] in (u'internal_api_error_DBConnectionError', u'internal_api_error_DBQueryError'):
                self.wait(token)
                return False
            if '*' in info['error']:
                raise errors.APIError(info['error']['code'],
                                      info['error']['info'], info['error']['*'])
            raise errors.APIError(info['error']['code'],
                                  info['error']['info'], kwargs)
        return True

    @staticmethod
    def _query_string(*args, **kwargs):
        kwargs.update(args)
        qs1 = [(k, v) for k, v in kwargs.iteritems() if k not in ('wpEditToken', 'token')]
        qs2 = [(k, v) for k, v in kwargs.iteritems() if k in ('wpEditToken', 'token')]
        return OrderedDict(qs1 + qs2)

    def raw_call(self, script, data, files=None):
        url = self.path + script + self.ext
        headers = {}
        if self.compress and gzip:
            headers['Accept-Encoding'] = 'gzip'
        token = self.wait_token((script, data))
        while True:
            scheme = 'http'  # Should we move to 'https' as default?
            host = self.host
            if isinstance(host, (list, tuple)):
                scheme, host = host

            fullurl = '{scheme}://{host}{url}'.format(scheme=scheme, host=host, url=url)

            try:
                stream = self.connection.post(fullurl, data=data, files=files, headers=headers)
                if stream.headers.get('x-database-lag'):
                    wait_time = int(stream.headers.get('retry-after'))
                    log.warn('Database lag exceeds max lag. Waiting for %d seconds', wait_time)
                    self.wait(token, wait_time)
                elif stream.status_code == 200:
                    return stream.text
                elif stream.status_code < 500 or stream.status_code > 599:
                    stream.raise_for_status()
                else:
                    log.warn('Received %s response: %s. Retrying in a moment.', stream.status_code, stream.text)
                    self.wait(token)

            except requests.exceptions.ConnectionError:
                # In the event of a network problem (e.g. DNS failure, refused connection, etc),
                # Requests will raise a ConnectionError exception.
                log.warn('Connection error. Retrying in a moment.')
                self.wait(token)

            except requests.exceptions.HTTPError as e:
                log.warn('HTTP error: %s', e.message)
                raise

            except requests.exceptions.TooManyRedirects:
                raise

    def raw_api(self, action, *args, **kwargs):
        """Sends a call to the API."""
        kwargs['action'] = action
        kwargs['format'] = 'json'
        data = self._query_string(*args, **kwargs)
        res = self.raw_call('api', data)

        try:
            return json.loads(res)
        except ValueError:
            if res.startswith('MediaWiki API is not enabled for this site.'):
                raise errors.APIDisabledError
            raise ValueError('Could not decode JSON: %s' % res)

    def raw_index(self, action, *args, **kwargs):
        """Sends a call to index.php rather than the API."""
        kwargs['action'] = action
        kwargs['maxlag'] = self.max_lag
        data = self._query_string(*args, **kwargs)
        return self.raw_call('index', data)

    def wait_token(self, args=None):
        token = WaitToken()
        self.wait_tokens[token] = (0, args)
        return token

    def wait(self, token, min_wait=0):
        retry, args = self.wait_tokens[token]
        self.wait_tokens[token] = (retry + 1, args)
        if retry > self.max_retries and self.max_retries != -1:
            raise errors.MaximumRetriesExceeded(self, token, args)
        self.wait_callback(self, token, retry, args)

        timeout = self.retry_timeout * retry
        if timeout < min_wait:
            timeout = min_wait
        log.debug('Sleeping for %d seconds', timeout)
        time.sleep(timeout)
        return self.wait_tokens[token]

    def require(self, major, minor, revision=None, raise_error=True):
        if self.version is None:
            if raise_error is None:
                return
            raise RuntimeError('Site %s has not yet been initialized' % repr(self))

        if revision is None:
            if self.version[:2] >= (major, minor):
                return True
            elif raise_error:
                raise errors.MediaWikiVersionError('Requires version %s.%s, current version is %s.%s'
                                                   % ((major, minor) + self.version[:2]))
            else:
                return False
        else:
            raise NotImplementedError

    # Actions
    def email(self, user, text, subject, cc=False):
        """
        Send email to a specified user on the wiki.

            >>> try:
            ...     site.email('SomeUser', 'Some message', 'Some subject')
            ... except mwclient.errors.NoSpecifiedEmailError as e:
            ...     print 'The user does not accept email, or has not specified an email address.'

        Args:
            user (str): User name of the recipient
            text (str): Body of the email
            subject (str): Subject of the email
            cc (bool): True to send a copy of the email to yourself (default is False)

        Returns:
            Dictionary of the JSON response

        Raises:
            NoSpecifiedEmailError (mwclient.errors.NoSpecifiedEmailError): if recipient does not accept email
            EmailError (mwclient.errors.EmailError): on other errors
        """

        token = self.get_token('email')

        try:
            info = self.api('emailuser', target=user, subject=subject,
                            text=text, ccme=cc, token=token)
        except errors.APIError as e:
            if e.args[0] == u'noemail':
                raise errors.NoSpecifiedEmail(user, e.args[1])
            raise errors.EmailError(*e)

        return info

    def login(self, username=None, password=None, cookies=None, domain=None):
        """Login to the wiki."""

        if username and password:
            self.credentials = (username, password, domain)
        if cookies:
            if self.host not in self.conn.cookies:
                self.conn.cookies[self.host] = http.CookieJar()
            self.conn.cookies[self.host].update(cookies)

        if self.credentials:
            wait_token = self.wait_token()
            kwargs = {
                'lgname': self.credentials[0],
                'lgpassword': self.credentials[1]
            }
            if self.credentials[2]:
                kwargs['lgdomain'] = self.credentials[2]
            while True:
                login = self.api('login', **kwargs)
                if login['login']['result'] == 'Success':
                    break
                elif login['login']['result'] == 'NeedToken':
                    kwargs['lgtoken'] = login['login']['token']
                elif login['login']['result'] == 'Throttled':
                    self.wait(wait_token, login['login'].get('wait', 5))
                else:
                    raise errors.LoginError(self, login['login'])

        if self.initialized:
            info = self.api('query', meta='userinfo', uiprop='groups|rights')
            userinfo = info['query']['userinfo']
            self.username = userinfo['name']
            self.groups = userinfo.get('groups', [])
            self.rights = userinfo.get('rights', [])
            self.tokens = {}
        else:
            self.site_init()

    def get_token(self, type, force=False, title=None):

        if self.version[:2] >= (1, 24):
            # The 'csrf' (cross-site request forgery) token introduced in 1.24 replaces
            # the majority of older tokens, like edittoken and movetoken.
            if type not in ['watch', 'patrol', 'rollback', 'userrights']:
                type = 'csrf'

        if type not in self.tokens:
            self.tokens[type] = '0'

        if self.tokens.get(type, '0') == '0' or force:

            if self.version[:2] >= (1, 24):
                info = self.api('query', meta='tokens', type=type)
                self.tokens[type] = info['query']['tokens']['%stoken' % type]

            else:
                if title is None:
                    # Some dummy title was needed to get a token prior to 1.24
                    title = 'Test'
                info = self.api('query', titles=title,
                                prop='info', intoken=type)
                for i in info['query']['pages'].itervalues():
                    if i['title'] == title:
                        self.tokens[type] = i['%stoken' % type]

        return self.tokens[type]

    def upload(self, file=None, filename=None, description='', ignore=False, file_size=None,
               url=None, filekey=None, comment=None):
        """
        Uploads a file to the site. Returns JSON result from the API.
        Can raise `errors.InsufficientPermission` and `requests.exceptions.HTTPError`.

        : Parameters :
          - file         : File object or stream to upload.
          - filename     : Destination filename, don't include namespace
                           prefix like 'File:'
          - description  : Wikitext for the file description page.
          - ignore       : True to upload despite any warnings.
          - file_size    : Deprecated in mwclient 0.7
          - url          : URL to fetch the file from.
          - filekey      : Key that identifies a previous upload that was
                           stashed temporarily.
          - comment      : Upload comment. Also used as the initial page text
                           for new files if `description` is not specified.

        Note that one of `file`, `filekey` and `url` must be specified, but not more
        than one. For normal uploads, you specify `file`.

        Example:

        >>> client.upload(open('somefile', 'rb'), filename='somefile.jpg',
                          description='Some description')
        """

        if file_size is not None:
            # Note that DeprecationWarning is hidden by default since Python 2.7
            warnings.warn(
                'file_size is deprecated since mwclient 0.7',
                DeprecationWarning
            )
            file_size = None

        if filename is None:
            raise TypeError('filename must be specified')

        if len([x for x in [file, filekey, url] if x is not None]) != 1:
            raise TypeError("exactly one of 'file', 'filekey' and 'url' must be specified")

        image = self.Images[filename]
        if not image.can('upload'):
            raise errors.InsufficientPermission(filename)

        predata = {}

        if comment is None:
            predata['comment'] = description
        else:
            predata['comment'] = comment
            predata['text'] = description

        if ignore:
            predata['ignorewarnings'] = 'true'
        predata['token'] = image.get_token('edit')
        predata['action'] = 'upload'
        predata['format'] = 'json'
        predata['filename'] = filename
        if url:
            predata['url'] = url

        # Renamed from sessionkey to filekey
        # https://git.wikimedia.org/commit/mediawiki%2Fcore.git/5f13517e
        if self.version[:2] < (1, 18):
            predata['sessionkey'] = filekey
        else:
            predata['filekey'] = filekey

        postdata = predata
        files = None
        if file is not None:

            # Workaround for https://github.com/mwclient/mwclient/issues/65
            # ----------------------------------------------------------------
            # Since the filename in Content-Disposition is not interpreted,
            # we can send some ascii-only dummy name rather than the real
            # filename, which might contain non-ascii.
            file = ('fake-filename', file)
            # End of workaround
            # ----------------------------------------------------------------

            files = {'file': file}

        wait_token = self.wait_token()
        while True:
            try:
                data = self.raw_call('api', postdata, files)
                info = json.loads(data)
                if not info:
                    info = {}
                if self.handle_api_result(info, kwargs=predata):
                    return info.get('upload', {})
            except requests.exceptions.HTTPError as e:
                if e.args[0] == 503 and e.args[1].getheader('X-Database-Lag'):
                    self.wait(wait_token, int(e.args[1].getheader('Retry-After')))
                elif e.args[0] < 500 or e.args[0] > 599:
                    raise
                else:
                    self.wait(wait_token)
            except requests.exceptions.ConnectionError:
                self.wait(wait_token)

    def parse(self, text=None, title=None, page=None):
        kwargs = {}
        if text is not None:
            kwargs['text'] = text
        if title is not None:
            kwargs['title'] = title
        if page is not None:
            kwargs['page'] = page
        result = self.api('parse', **kwargs)
        return result['parse']

    # def block(self): TODO?
    # def unblock: TODO?
    # def patrol: TODO?
    # def import: TODO?

    # Lists
    def allpages(self, start=None, prefix=None, namespace='0', filterredir='all',
                 minsize=None, maxsize=None, prtype=None, prlevel=None,
                 limit=None, dir='ascending', filterlanglinks='all', generator=True):
        """Retrieve all pages on the wiki as a generator."""

        pfx = listing.List.get_prefix('ap', generator)
        kwargs = dict(listing.List.generate_kwargs(pfx, ('from', start), prefix=prefix,
                                                   minsize=minsize, maxsize=maxsize, prtype=prtype, prlevel=prlevel,
                                                   namespace=namespace, filterredir=filterredir, dir=dir,
                                                   filterlanglinks=filterlanglinks))
        return listing.List.get_list(generator)(self, 'allpages', 'ap', limit=limit, return_values='title', **kwargs)

    def allimages(self, start=None, prefix=None, minsize=None, maxsize=None, limit=None,
                  dir='ascending', sha1=None, sha1base36=None, prop='timestamp|url',
                  generator=True):
        """Retrieve all images on the wiki as a generator."""

        pfx = listing.List.get_prefix('ai', generator)
        kwargs = dict(listing.List.generate_kwargs(pfx, ('from', start), prefix=prefix,
                                                   minsize=minsize, maxsize=maxsize,
                                                   dir=dir, sha1=sha1, sha1base36=sha1base36))
        return listing.List.get_list(generator)(self, 'allimages', 'ai', limit=limit, return_values='timestamp|url', **kwargs)

    def alllinks(self, start=None, prefix=None, unique=False, prop='title',
                 namespace='0', limit=None, generator=True):
        """Retrieve a list of all links on the wiki as a generator."""

        pfx = listing.List.get_prefix('al', generator)
        kwargs = dict(listing.List.generate_kwargs(pfx, ('from', start), prefix=prefix,
                                                   prop=prop, namespace=namespace))
        if unique:
            kwargs[pfx + 'unique'] = '1'
        return listing.List.get_list(generator)(self, 'alllinks', 'al', limit=limit, return_values='title', **kwargs)

    def allcategories(self, start=None, prefix=None, dir='ascending', limit=None, generator=True):
        """Retrieve all categories on the wiki as a generator."""

        pfx = listing.List.get_prefix('ac', generator)
        kwargs = dict(listing.List.generate_kwargs(pfx, ('from', start), prefix=prefix, dir=dir))
        return listing.List.get_list(generator)(self, 'allcategories', 'ac', limit=limit, **kwargs)

    def allusers(self, start=None, prefix=None, group=None, prop=None, limit=None,
                 witheditsonly=False, activeusers=False, rights=None):
        """Retrieve all users on the wiki as a generator."""

        kwargs = dict(listing.List.generate_kwargs('au', ('from', start), prefix=prefix,
                                                   group=group, prop=prop,
                                                   rights=rights,
                                                   witheditsonly=witheditsonly,
                                                   activeusers=activeusers))
        print kwargs
        return listing.List(self, 'allusers', 'au', limit=limit, **kwargs)

    def blocks(self, start=None, end=None, dir='older', ids=None, users=None, limit=None,
               prop='id|user|by|timestamp|expiry|reason|flags'):
        """Retrieve blocks as a generator.

        Each block is a dictionary containing:
        - user: the username or IP address of the user
        - id: the ID of the block
        - timestamp: when the block was added
        - expiry: when the block runs out (infinity for indefinite blocks)
        - reason: the reason they are blocked
        - allowusertalk: key is present (empty string) if the user is allowed to edit their user talk page
        - by: the administrator who blocked the user
        - nocreate: key is present (empty string) if the user's ability to create accounts has been disabled.

        """

        # TODO: Fix. Fix what?
        kwargs = dict(listing.List.generate_kwargs('bk', start=start, end=end, dir=dir,
                                                   users=users, prop=prop))
        return listing.List(self, 'blocks', 'bk', limit=limit, **kwargs)

    def deletedrevisions(self, start=None, end=None, dir='older', namespace=None,
                         limit=None, prop='user|comment'):
        # TODO: Fix

        kwargs = dict(listing.List.generate_kwargs('dr', start=start, end=end, dir=dir,
                                                   namespace=namespace, prop=prop))
        return listing.List(self, 'deletedrevs', 'dr', limit=limit, **kwargs)

    def exturlusage(self, query, prop=None, protocol='http', namespace=None, limit=None):
        """Retrieves list of pages that link to a particular domain or URL as a generator.

        This API call mirrors the Special:LinkSearch function on-wiki.

        Query can be a domain like 'bbc.co.uk'. Wildcards can be used, e.g. '*.bbc.co.uk'.
        Alternatively, a query can contain a full domain name and some or all of a URL:
        e.g. '*.wikipedia.org/wiki/*'

        See <https://meta.wikimedia.org/wiki/Help:Linksearch> for details.

        The generator returns dictionaries containing three keys:
        - url: the URL linked to.
        - ns: namespace of the wiki page
        - pageid: the ID of the wiki page
        - title: the page title.

        """

        kwargs = dict(listing.List.generate_kwargs('eu', query=query, prop=prop,
                                                   protocol=protocol, namespace=namespace))
        return listing.List(self, 'exturlusage', 'eu', limit=limit, **kwargs)

    def logevents(self, type=None, prop=None, start=None, end=None,
                  dir='older', user=None, title=None, limit=None, action=None):

        kwargs = dict(listing.List.generate_kwargs('le', prop=prop, type=type, start=start,
                                                   end=end, dir=dir, user=user, title=title, action=action))
        return listing.List(self, 'logevents', 'le', limit=limit, **kwargs)

    # def protectedtitles requires 1.15
    def random(self, namespace, limit=20):
        """Retrieves a generator of random page from a particular namespace.

        limit specifies the number of random articles retrieved.
        namespace is a namespace identifier integer.

        Generator contains dictionary with namespace, page ID and title.

        """

        kwargs = dict(listing.List.generate_kwargs('rn', namespace=namespace))
        return listing.List(self, 'random', 'rn', limit=limit, **kwargs)

    def recentchanges(self, start=None, end=None, dir='older', namespace=None,
                      prop=None, show=None, limit=None, type=None):

        kwargs = dict(listing.List.generate_kwargs('rc', start=start, end=end, dir=dir,
                                                   namespace=namespace, prop=prop, show=show, type=type))
        return listing.List(self, 'recentchanges', 'rc', limit=limit, **kwargs)

    def search(self, search, namespace='0', what='title', redirects=False, limit=None):

        kwargs = dict(listing.List.generate_kwargs('sr', search=search, namespace=namespace, what=what))
        if redirects:
            kwargs['srredirects'] = '1'
        return listing.List(self, 'search', 'sr', limit=limit, **kwargs)

    def usercontributions(self, user, start=None, end=None, dir='older', namespace=None,
                          prop=None, show=None, limit=None):

        kwargs = dict(listing.List.generate_kwargs('uc', user=user, start=start, end=end,
                                                   dir=dir, namespace=namespace, prop=prop, show=show))
        return listing.List(self, 'usercontribs', 'uc', limit=limit, **kwargs)

    def users(self, users, prop='blockinfo|groups|editcount'):

        return listing.List(self, 'users', 'us', ususers='|'.join(users), usprop=prop)

    def watchlist(self, allrev=False, start=None, end=None, namespace=None, dir='older',
                  prop=None, show=None, limit=None):

        kwargs = dict(listing.List.generate_kwargs('wl', start=start, end=end,
                                                   namespace=namespace, dir=dir, prop=prop, show=show))
        if allrev:
            kwargs['wlallrev'] = '1'
        return listing.List(self, 'watchlist', 'wl', limit=limit, **kwargs)

    def expandtemplates(self, text, title=None, generatexml=False):
        """Takes wikitext (text) and expands templates."""

        kwargs = {}
        if title is None:
            kwargs['title'] = title
        if generatexml:
            kwargs['generatexml'] = '1'

        result = self.api('expandtemplates', text=text, **kwargs)

        if generatexml:
            return result['expandtemplates']['*'], result['parsetree']['*']
        else:
            return result['expandtemplates']['*']

    def ask(self, query, title=None):
        """Ask a query against Semantic MediaWiki."""
        kwargs = {}
        if title is None:
            kwargs['title'] = title
        result = self.raw_api('ask', query=query, **kwargs)
        return result['query']['results']
