# encoding=utf-8
import warnings
import logging
from six import text_type
import six

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

import mwclient.errors as errors
import mwclient.listing as listing
from mwclient.sleep import Sleepers
from mwclient.util import parse_timestamp

try:
    import gzip
except ImportError:
    gzip = None

__ver__ = '0.8.2.dev1'

log = logging.getLogger(__name__)


class Site(object):
    """
    A MediaWiki site identified by its hostname.

        >>> import mwclient
        >>> site = mwclient.Site('en.wikipedia.org')

    Do not include the leading "http://".

    Mwclient assumes that the script path (where index.php and api.php are located)
    is '/w/'. If the site uses a different script path, you must specify this
    (path must end in a '/'). Examples:

        >>> site = mwclient.Site('vim.wikia.com', path='/')
        >>> site = mwclient.Site('sourceforge.net', path='/apps/mediawiki/mwclient/')

    """
    api_limit = 500

    def __init__(self, host, path='/w/', ext='.php', pool=None, retry_timeout=30,
                 max_retries=25, wait_callback=lambda *x: None, clients_useragent=None,
                 max_lag=3, compress=True, force_login=True, do_init=True, httpauth=None,
                 reqs=None):
        # Setup member variables
        self.host = host
        self.path = path
        self.ext = ext
        self.credentials = None
        self.compress = compress
        self.max_lag = text_type(max_lag)
        self.force_login = force_login
        self.requests = reqs or {}

        if isinstance(httpauth, (list, tuple)):
            self.httpauth = HTTPBasicAuth(*httpauth)
        elif httpauth is None or isinstance(httpauth, (AuthBase,)):
            self.httpauth = httpauth
        else:
            raise RuntimeError('Authentication is not a tuple or an instance of AuthBase')

        self.sleepers = Sleepers(max_retries, retry_timeout, wait_callback)

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
                        siprop='general|namespaces', uiprop='groups|rights', retry_on_error=False)

        # Extract site info
        self.site = meta['query']['general']
        self.namespaces = dict(((i['id'], i.get('*', '')) for i in six.itervalues(meta['query']['namespaces'])))
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
            ...         print '{} {} {}'.format(page['title'],
            ...             page['coordinates'][0]['lat'],
            ...             page['coordinates'][0]['lon'])
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

        sleeper = self.sleepers.make()

        while True:
            info = self.raw_api(action, **kwargs)
            if not info:
                info = {}
            if self.handle_api_result(info, sleeper=sleeper):
                return info

    def handle_api_result(self, info, kwargs=None, sleeper=None):
        if sleeper is None:
            sleeper = self.sleepers.make()

        try:
            userinfo = info['query']['userinfo']
        except KeyError:
            userinfo = ()
        if 'blockedby' in userinfo:
            self.blocked = (userinfo['blockedby'], userinfo.get('blockreason', u''))
        else:
            self.blocked = False
        self.hasmsg = 'messages' in userinfo
        self.logged_in = 'anon' not in userinfo
        if 'error' in info:
            if info['error']['code'] in (u'internal_api_error_DBConnectionError', u'internal_api_error_DBQueryError'):
                sleeper.sleep()
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
        qs1 = [(k, v) for k, v in six.iteritems(kwargs) if k not in ('wpEditToken', 'token')]
        qs2 = [(k, v) for k, v in six.iteritems(kwargs) if k in ('wpEditToken', 'token')]
        return OrderedDict(qs1 + qs2)

    def raw_call(self, script, data, files=None, retry_on_error=True):
        """
        Perform a generic request and return the raw text.

        In the event of a network problem, or a HTTP response with status code 5XX,
        we'll wait and retry the configured number of times before giving up
        if `retry_on_error` is True.

        `requests.exceptions.HTTPError` is still raised directly for
        HTTP responses with status codes in the 4XX range, and invalid
        HTTP responses.

        Args:
            script (str): Script name, usually 'api'.
            data (dict): Post data
            files (dict): Files to upload
            retry_on_error (bool): Retry on connection error

        Returns:
            The raw text response.
        """
        url = self.path + script + self.ext
        headers = {}
        if self.compress and gzip:
            headers['Accept-Encoding'] = 'gzip'
        sleeper = self.sleepers.make((script, data))
        while True:
            scheme = 'https'
            host = self.host
            if isinstance(host, (list, tuple)):
                scheme, host = host

            fullurl = '{scheme}://{host}{url}'.format(scheme=scheme, host=host, url=url)

            try:
                stream = self.connection.post(fullurl, data=data, files=files, headers=headers, **self.requests)
                if stream.headers.get('x-database-lag'):
                    wait_time = int(stream.headers.get('retry-after'))
                    log.warning('Database lag exceeds max lag. Waiting for %d seconds', wait_time)
                    sleeper.sleep(wait_time)
                elif stream.status_code == 200:
                    return stream.text
                elif stream.status_code < 500 or stream.status_code > 599:
                    stream.raise_for_status()
                else:
                    if not retry_on_error:
                        stream.raise_for_status()
                    log.warning('Received %s response: %s. Retrying in a moment.', stream.status_code, stream.text)
                    sleeper.sleep()

            except requests.exceptions.ConnectionError:
                # In the event of a network problem (e.g. DNS failure, refused connection, etc),
                # Requests will raise a ConnectionError exception.
                if not retry_on_error:
                    raise
                log.warning('Connection error. Retrying in a moment.')
                sleeper.sleep()

    def raw_api(self, action, *args, **kwargs):
        """Sends a call to the API."""
        try:
            retry_on_error = kwargs.pop('retry_on_error')
        except KeyError:
            retry_on_error = True
        kwargs['action'] = action
        kwargs['format'] = 'json'
        data = self._query_string(*args, **kwargs)
        res = self.raw_call('api', data, retry_on_error=retry_on_error)

        try:
            return json.loads(res)
        except ValueError:
            if res.startswith('MediaWiki API is not enabled for this site.'):
                raise errors.APIDisabledError
            raise errors.InvalidResponse(res)

    def raw_index(self, action, *args, **kwargs):
        """Sends a call to index.php rather than the API."""
        kwargs['action'] = action
        kwargs['maxlag'] = self.max_lag
        data = self._query_string(*args, **kwargs)
        return self.raw_call('index', data)

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
            self.connection.cookies.update(cookies)

        if self.credentials:
            sleeper = self.sleepers.make()
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
                    sleeper.sleep(int(login['login'].get('wait', 5)))
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
                for i in six.itervalues(info['query']['pages']):
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

        # sessionkey was renamed to filekey in MediaWiki 1.18
        # https://phabricator.wikimedia.org/rMW5f13517e36b45342f228f3de4298bb0fe186995d
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

        sleeper = self.sleepers.make()
        while True:
            data = self.raw_call('api', postdata, files)
            info = json.loads(data)
            if not info:
                info = {}
            if self.handle_api_result(info, kwargs=predata, sleeper=sleeper):
                return info.get('upload', {})

    def parse(self, text=None, title=None, page=None, prop=None, redirects=False, mobileformat=False):
        kwargs = {}
        if text is not None:
            kwargs['text'] = text
        if title is not None:
            kwargs['title'] = title
        if page is not None:
            kwargs['page'] = page
        if prop is not None:
            kwargs['prop'] = prop
        if redirects:
            kwargs['redirects'] = '1'
        if mobileformat:
            kwargs['mobileformat'] = '1'
        result = self.api('parse', **kwargs)
        return result['parse']

    # def block(self): TODO?
    # def unblock: TODO?
    # def patrol: TODO?
    # def import: TODO?

    # Lists
    def allpages(self, start=None, prefix=None, namespace='0', filterredir='all',
                 minsize=None, maxsize=None, prtype=None, prlevel=None,
                 limit=None, dir='ascending', filterlanglinks='all', generator=True,
                 end=None):
        """Retrieve all pages on the wiki as a generator."""

        pfx = listing.List.get_prefix('ap', generator)
        kwargs = dict(listing.List.generate_kwargs(pfx, ('from', start), ('to', end), prefix=prefix,
                                                   minsize=minsize, maxsize=maxsize, prtype=prtype, prlevel=prlevel,
                                                   namespace=namespace, filterredir=filterredir, dir=dir,
                                                   filterlanglinks=filterlanglinks))
        return listing.List.get_list(generator)(self, 'allpages', 'ap', limit=limit, return_values='title', **kwargs)

    def allimages(self, start=None, prefix=None, minsize=None, maxsize=None, limit=None,
                  dir='ascending', sha1=None, sha1base36=None, generator=True, end=None):
        """Retrieve all images on the wiki as a generator."""

        pfx = listing.List.get_prefix('ai', generator)
        kwargs = dict(listing.List.generate_kwargs(pfx, ('from', start), ('to', end), prefix=prefix,
                                                   minsize=minsize, maxsize=maxsize,
                                                   dir=dir, sha1=sha1, sha1base36=sha1base36))
        return listing.List.get_list(generator)(self, 'allimages', 'ai', limit=limit, return_values='timestamp|url', **kwargs)

    def alllinks(self, start=None, prefix=None, unique=False, prop='title',
                 namespace='0', limit=None, generator=True, end=None):
        """Retrieve a list of all links on the wiki as a generator."""

        pfx = listing.List.get_prefix('al', generator)
        kwargs = dict(listing.List.generate_kwargs(pfx, ('from', start), ('to', end), prefix=prefix,
                                                   prop=prop, namespace=namespace))
        if unique:
            kwargs[pfx + 'unique'] = '1'
        return listing.List.get_list(generator)(self, 'alllinks', 'al', limit=limit, return_values='title', **kwargs)

    def allcategories(self, start=None, prefix=None, dir='ascending', limit=None, generator=True,
                      end=None):
        """Retrieve all categories on the wiki as a generator."""

        pfx = listing.List.get_prefix('ac', generator)
        kwargs = dict(listing.List.generate_kwargs(pfx, ('from', start), ('to', end), prefix=prefix, dir=dir))
        return listing.List.get_list(generator)(self, 'allcategories', 'ac', limit=limit, **kwargs)

    def allusers(self, start=None, prefix=None, group=None, prop=None, limit=None,
                 witheditsonly=False, activeusers=False, rights=None, end=None):
        """Retrieve all users on the wiki as a generator."""

        kwargs = dict(listing.List.generate_kwargs('au', ('from', start), ('to', end), prefix=prefix,
                                                   group=group, prop=prop,
                                                   rights=rights,
                                                   witheditsonly=witheditsonly,
                                                   activeusers=activeusers))
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
                                                   ids=ids, users=users, prop=prop))
        return listing.List(self, 'blocks', 'bk', limit=limit, **kwargs)

    def deletedrevisions(self, start=None, end=None, dir='older', namespace=None,
                         limit=None, prop='user|comment'):
        # TODO: Fix

        kwargs = dict(listing.List.generate_kwargs('dr', start=start, end=end, dir=dir,
                                                   namespace=namespace, prop=prop))
        return listing.List(self, 'deletedrevs', 'dr', limit=limit, **kwargs)

    def exturlusage(self, query, prop=None, protocol='http', namespace=None, limit=None):
        r"""Retrieves list of pages that link to a particular domain or URL as a generator.

        This API call mirrors the Special:LinkSearch function on-wiki.

        Query can be a domain like 'bbc.co.uk'. Wildcards can be used, e.g. '\*.bbc.co.uk'.
        Alternatively, a query can contain a full domain name and some or all of a URL:
        e.g. '\*.wikipedia.org/wiki/\*'

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
        """Retrieve logevents as a generator."""
        kwargs = dict(listing.List.generate_kwargs('le', prop=prop, type=type, start=start,
                                                   end=end, dir=dir, user=user, title=title, action=action))
        return listing.List(self, 'logevents', 'le', limit=limit, **kwargs)

    def checkuserlog(self, user=None, target=None, limit=10, dir='older', start=None, end=None):
        """Retrieve checkuserlog items as a generator."""

        kwargs = dict(listing.List.generate_kwargs('cul', target=target, start=start,
                                                   end=end, dir=dir, user=user))
        return listing.NestedList('entries', self, 'checkuserlog', 'cul', limit=limit, **kwargs)

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
                      prop=None, show=None, limit=None, type=None, toponly=None):
        """
        List recent changes to the wiki, à la Special:Recentchanges.
        """
        kwargs = dict(listing.List.generate_kwargs('rc', start=start, end=end, dir=dir,
                                                   namespace=namespace, prop=prop, show=show, type=type,
                                                   toponly='1' if toponly else None))
        return listing.List(self, 'recentchanges', 'rc', limit=limit, **kwargs)

    def revisions(self, revids, prop='ids|timestamp|flags|comment|user',
                  expandtemplates=False, diffto='prev'):
        """
        Get data about a list of revisions. See also the `Page.revisions()`
        method.
        API doc: https://www.mediawiki.org/wiki/API:Revisions

        Example: Get revision text for two revisions:

            >>> for revision in site.revisions([689697696, 689816909], prop='content'):
            ...     print revision['*']

        Args:
            revids (list): A list of (max 50) revisions.
            prop (str): Which properties to get for each revision.
            expandtemplates (bool): Expand templates in `rvprop=content` output.
            diffto (str): Revision ID to diff each revision to. Use "prev",
                          "next" and "cur" for the previous, next and current
                          revision respectively.

        Returns:
            A list of revisions
        """
        kwargs = {
            'prop': 'revisions',
            'rvprop': prop,
            'revids': '|'.join(map(text_type, revids))
        }
        if expandtemplates:
            kwargs['rvexpandtemplates'] = '1'
        if diffto:
            kwargs['rvdiffto'] = diffto

        revisions = []
        pages = self.api('query', **kwargs).get('query', {}).get('pages', {}).values()
        for page in pages:
            for revision in page.get('revisions', ()):
                revision['pageid'] = page.get('pageid')
                revision['pagetitle'] = page.get('title')
                revision['timestamp'] = parse_timestamp(revision['timestamp'])
                revisions.append(revision)
        return revisions

    def search(self, search, namespace='0', what=None, redirects=False, limit=None):
        """
        Perform a full text search.
        API doc: https://www.mediawiki.org/wiki/API:Search

            >>> for result in site.search('prefix:Template:Citation/'):
            ...     print(result.get('title'))

        Args:
            search (str): The query string
            namespace (int): The namespace to search (default: 0)
            what (str): Search scope: 'text' for fulltext, or 'title' for titles only.
                        Depending on the search backend, both options may not be available.
                        For instance
                        `CirrusSearch <https://www.mediawiki.org/wiki/Help:CirrusSearch>`_
                        doesn't support 'title', but instead provides an "intitle:"
                        query string filter.
            redirects (bool): Include redirect pages in the search (option removed in MediaWiki 1.23).

        Returns:
            mwclient.listings.List: Search results iterator
        """
        kwargs = dict(listing.List.generate_kwargs('sr', search=search, namespace=namespace, what=what))
        if redirects:
            kwargs['srredirects'] = '1'
        return listing.List(self, 'search', 'sr', limit=limit, **kwargs)

    def usercontributions(self, user, start=None, end=None, dir='older', namespace=None,
                          prop=None, show=None, limit=None):
        """
        List the contributions made by a given user to the wiki, à la Special:Contributions.

        API doc: https://www.mediawiki.org/wiki/API:Usercontribs
        """
        kwargs = dict(listing.List.generate_kwargs('uc', user=user, start=start, end=end,
                                                   dir=dir, namespace=namespace, prop=prop, show=show))
        return listing.List(self, 'usercontribs', 'uc', limit=limit, **kwargs)

    def users(self, users, prop='blockinfo|groups|editcount'):
        """
        Get information about a list of users.

        API doc: https://www.mediawiki.org/wiki/API:Users
        """

        return listing.List(self, 'users', 'us', ususers='|'.join(users), usprop=prop)

    def watchlist(self, allrev=False, start=None, end=None, namespace=None, dir='older',
                  prop=None, show=None, limit=None):
        """
        List the pages on the current user's watchlist.

        API doc: https://www.mediawiki.org/wiki/API:Watchlist
        """

        kwargs = dict(listing.List.generate_kwargs('wl', start=start, end=end,
                                                   namespace=namespace, dir=dir, prop=prop, show=show))
        if allrev:
            kwargs['wlallrev'] = '1'
        return listing.List(self, 'watchlist', 'wl', limit=limit, **kwargs)

    def expandtemplates(self, text, title=None, generatexml=False):
        """
        Takes wikitext (text) and expands templates.

        API doc: https://www.mediawiki.org/wiki/API:Expandtemplates
        """

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
        """
        Ask a query against Semantic MediaWiki.

        API doc: https://semantic-mediawiki.org/wiki/Ask_API
        """
        kwargs = {}
        if title is None:
            kwargs['title'] = title
        result = self.raw_api('ask', query=query, **kwargs)
        return result['query']['results']
