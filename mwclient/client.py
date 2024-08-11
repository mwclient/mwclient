import warnings
import logging

from collections import OrderedDict

import json
import requests
from requests.auth import HTTPBasicAuth, AuthBase
from requests_oauthlib import OAuth1

import mwclient.errors as errors
import mwclient.listing as listing
from mwclient.sleep import Sleepers
from mwclient.util import parse_timestamp, read_in_chunks, handle_limit

__version__ = '0.11.0'

log = logging.getLogger(__name__)

USER_AGENT = 'mwclient/{} ({})'.format(__version__,
                                       'https://github.com/mwclient/mwclient')


class Site:
    """A MediaWiki site identified by its hostname.

    Examples:
        >>> import mwclient
        >>> wikipedia_site = mwclient.Site('en.wikipedia.org')
        >>> wikia_site = mwclient.Site('vim.wikia.com', path='/')

    Args:
        host (str): The hostname of a MediaWiki instance. Must not include a
            scheme (e.g. `https://`) - use the `scheme` argument instead.
        path (str): The instances script path (where the `index.php` and `api.php` scripts
            are located). Must contain a trailing slash (`/`). Defaults to `/w/`.
        ext (str): The file extension used by the MediaWiki API scripts. Defaults to
            `.php`.
        pool (requests.Session): A preexisting :class:`~requests.Session` to be used when
            executing API requests.
        retry_timeout (int): The number of seconds to sleep for each past retry of a
            failing API request. Defaults to `30`.
        max_retries (int): The maximum number of retries to perform for failing API
            requests. Defaults to `25`.
        wait_callback (Callable): A callback function to be executed for each failing
            API request.
        clients_useragent (str): A prefix to be added to the default mwclient user-agent.
            Should follow the pattern `'{tool_name}/{tool_version} ({contact})'`. Check
            the `User-Agent policy <https://meta.wikimedia.org/wiki/User-Agent_policy>`_
            for more information.
        max_lag (int): A `maxlag` parameter to be used in `index.php` calls. Consult the
            `documentation <https://www.mediawiki.org/wiki/Manual:Maxlag_parameter>`_ for
            more information. Defaults to `3`.
        compress (bool): Whether to request and accept gzip compressed API responses.
            Defaults to `True`.
        force_login (bool): Whether to require authentication when editing pages. Set to
            `False` to allow unauthenticated edits. Defaults to `True`.
        do_init (bool): Whether to automatically initialize the :py:class:`Site` on
            initialization. When set to `False`, the :py:class:`Site` must be initialized
            manually using the :py:meth:`.site_init` method. Defaults to `True`.
        httpauth (Union[tuple[basestring, basestring], requests.auth.AuthBase]): An
            authentication method to be used when making API requests. This can be either
            an authentication object as provided by the :py:mod:`requests` library, or a
            tuple in the form `{username, password}`. Usernames and passwords provided as
            text strings are encoded as UTF-8. If dealing with a server that cannot
            handle UTF-8, please provide the username and password already encoded with
            the appropriate encoding.
        connection_options (Dict[str, Any]): Additional arguments to be passed to the
            :py:meth:`requests.Session.request` method when performing API calls. If the
            `timeout` key is empty, a default timeout of 30 seconds is added.
        consumer_token (str): OAuth1 consumer key for owner-only consumers.
        consumer_secret (str): OAuth1 consumer secret for owner-only consumers.
        access_token (str): OAuth1 access key for owner-only consumers.
        access_secret (str): OAuth1 access secret for owner-only consumers.
        client_certificate (Union[str, tuple[str, str]]): A client certificate to be added
            to the session.
        custom_headers (Dict[str, str]): A dictionary of custom headers to be added to all
            API requests.
        scheme (str): The URI scheme to use. This should be either `http` or `https` in
            most cases. Defaults to `https`.

    Raises:
        RuntimeError: The authentication passed to the `httpauth` parameter is invalid.
            You must pass either a tuple or a :class:`requests.auth.AuthBase` object.
        errors.OAuthAuthorizationError: The OAuth authorization is invalid.
        errors.LoginError: Login failed, the reason can be obtained from e.code and e.info
            (where e is the exception object) and will be one of the API:Login errors. The
            most common error code is "Failed", indicating a wrong username or password.
    """
    api_limit = 500

    def __init__(self, host, path='/w/', ext='.php', pool=None, retry_timeout=30,
                 max_retries=25, wait_callback=lambda *x: None, clients_useragent=None,
                 max_lag=3, compress=True, force_login=True, do_init=True, httpauth=None,
                 connection_options=None, consumer_token=None, consumer_secret=None,
                 access_token=None, access_secret=None, client_certificate=None,
                 custom_headers=None, scheme='https', reqs=None):
        # Setup member variables
        self.host = host
        self.path = path
        self.ext = ext
        self.credentials = None
        self.compress = compress
        self.max_lag = str(max_lag)
        self.force_login = force_login
        if reqs and connection_options:
            raise ValueError(
                "reqs is a deprecated alias of connection_options. Do not specify both."
            )
        if reqs:
            warnings.warn(
                "reqs is deprecated in mwclient 1.0.0. Use connection_options instead",
                DeprecationWarning
            )
            connection_options = reqs
        self.requests = connection_options or {}
        self.scheme = scheme
        if 'timeout' not in self.requests:
            self.requests['timeout'] = 30  # seconds

        if consumer_token is not None:
            auth = OAuth1(consumer_token, consumer_secret, access_token, access_secret)
        elif isinstance(httpauth, (list, tuple)):
            # workaround weird requests default to encode as latin-1
            # https://github.com/mwclient/mwclient/issues/315
            # https://github.com/psf/requests/issues/4564
            httpauth = [
                it.encode("utf-8") if isinstance(it, str) else it for it in httpauth
            ]
            auth = HTTPBasicAuth(*httpauth)
        elif httpauth is None or isinstance(httpauth, (AuthBase,)):
            auth = httpauth
        else:
            # FIXME: Raise a specific exception instead of a generic RuntimeError.
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

        # Setup connection
        if pool is None:
            self.connection = requests.Session()
            self.connection.auth = auth
            if client_certificate:
                self.connection.cert = client_certificate

            # Set User-Agent header field
            if clients_useragent:
                ua = clients_useragent + ' ' + USER_AGENT
            else:
                ua = USER_AGENT
            self.connection.headers['User-Agent'] = ua

            if custom_headers:
                self.connection.headers.update(custom_headers)
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

        # Upload chunk size in bytes
        self.chunk_size = 1048576

        if do_init:
            try:
                self.site_init()
            except errors.APIError as e:
                if e.args[0] == 'mwoauth-invalid-authorization':
                    raise errors.OAuthAuthorizationError(self, e.code, e.info)

                # Private wiki, do init after login
                if e.args[0] not in {'unknown_action', 'readapidenied'}:
                    raise

    def site_init(self):
        """Populates the object with information about the current user and site. This is
        done automatically when creating the object, unless explicitly disabled using the
        `do_init=False` constructor argument."""

        if self.initialized:
            info = self.get('query', meta='userinfo', uiprop='groups|rights')
            userinfo = info['query']['userinfo']
            self.username = userinfo['name']
            self.groups = userinfo.get('groups', [])
            self.rights = userinfo.get('rights', [])
            self.tokens = {}
            return

        meta = self.get('query', meta='siteinfo|userinfo',
                        siprop='general|namespaces', uiprop='groups|rights',
                        retry_on_error=False)

        # Extract site info
        self.site = meta['query']['general']
        self.namespaces = {
            namespace['id']: namespace.get('*', '')
            for namespace in meta['query']['namespaces'].values()
        }

        self.version = self.version_tuple_from_generator(self.site['generator'])

        # Require MediaWiki version >= 1.16
        self.require(1, 16)

        # User info
        userinfo = meta['query']['userinfo']
        self.username = userinfo['name']
        self.groups = userinfo.get('groups', [])
        self.rights = userinfo.get('rights', [])
        self.initialized = True

    @staticmethod
    def version_tuple_from_generator(string, prefix='MediaWiki '):
        """Return a version tuple from a MediaWiki Generator string.

        Example:
            >>> Site.version_tuple_from_generator("MediaWiki 1.5.1")
            (1, 5, 1)

        Args:
            string (str): The MediaWiki Generator string.
            prefix (str): The expected prefix of the string.

        Returns:
            A tuple containing the individual elements of the given version number.
        """
        if not string.startswith(prefix):
            raise errors.MediaWikiVersionError('Unknown generator {}'.format(string))

        version = string[len(prefix):].split('.')

        def split_num(s):
            """Split the string on the first non-digit character.

            Returns:
                A tuple of the digit part as int and, if available,
                the rest of the string.
            """
            i = 0
            while i < len(s):
                if s[i] < '0' or s[i] > '9':
                    break
                i += 1
            if s[i:]:
                return (int(s[:i]), s[i:], )
            else:
                return (int(s[:i]), )

        version_tuple = sum((split_num(s) for s in version), ())

        if len(version_tuple) < 2:
            raise errors.MediaWikiVersionError('Unknown MediaWiki {}'
                                               .format('.'.join(version)))

        return version_tuple

    default_namespaces = {
        0: '', 1: 'Talk', 2: 'User', 3: 'User talk', 4: 'Project',
        5: 'Project talk', 6: 'Image', 7: 'Image talk', 8: 'MediaWiki',
        9: 'MediaWiki talk', 10: 'Template', 11: 'Template talk', 12: 'Help',
        13: 'Help talk', 14: 'Category', 15: 'Category talk',
        -1: 'Special', -2: 'Media'
    }

    def __repr__(self):
        return "<%s object '%s%s'>" % (self.__class__.__name__, self.host, self.path)

    def get(self, action, *args, **kwargs):
        """Perform a generic API call using GET.

        This is just a shorthand for calling api() with http_method='GET'.
        All arguments will be passed on.

        Args:
            action (str): The MediaWiki API action to be performed.

        Returns:
            The raw response from the API call, as a dictionary.
        """
        return self.api(action, 'GET', *args, **kwargs)

    def post(self, action, *args, **kwargs):
        """Perform a generic API call using POST.

        This is just a shorthand for calling api() with http_method='POST'.
        All arguments will be passed on.

        Args:
            action (str): The MediaWiki API action to be performed.

        Returns:
            The raw response from the API call, as a dictionary.
        """
        return self.api(action, 'POST', *args, **kwargs)

    def api(self, action, http_method='POST', *args, **kwargs):
        """Perform a generic API call and handle errors.

        All arguments will be passed on.

        Args:
            action (str): The MediaWiki API action to be performed.
            http_method (str): The HTTP method to use.

        Example:
            To get coordinates from the GeoData MediaWiki extension at English Wikipedia:

            >>> site = Site('en.wikipedia.org')
            >>> result = site.api('query', prop='coordinates', titles='Oslo|Copenhagen')
            >>> for page in result['query']['pages'].values():
            ...     if 'coordinates' in page:
            ...         print('{} {} {}'.format(page['title'],
            ...             page['coordinates'][0]['lat'],
            ...             page['coordinates'][0]['lon']))
            Oslo 59.95 10.75
            Copenhagen 55.6761 12.5683

        Returns:
            The raw response from the API call, as a dictionary.
        """
        kwargs.update(args)

        if action == 'query' and 'continue' not in kwargs:
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
            info = self.raw_api(action, http_method, **kwargs)
            if not info:
                info = {}
            if self.handle_api_result(info, sleeper=sleeper):
                return info

    def handle_api_result(self, info, kwargs=None, sleeper=None):
        """Checks the given API response, raising an appropriate exception or sleeping if
        necessary.

        Args:
            info (dict): The API result.
            kwargs (dict): Additional arguments to be passed when raising an
                :class:`errors.APIError`.
            sleeper (sleep.Sleeper): A :class:`~sleep.Sleeper` instance to use when
                sleeping.

        Returns:
            `False` if the given API response contains an exception, else `True`.
        """

        if sleeper is None:
            sleeper = self.sleepers.make()

        try:
            userinfo = info['query']['userinfo']
        except KeyError:
            userinfo = ()
        if 'blockedby' in userinfo:
            self.blocked = (userinfo['blockedby'], userinfo.get('blockreason', ''))
        else:
            self.blocked = False
        self.hasmsg = 'messages' in userinfo
        self.logged_in = 'anon' not in userinfo
        if 'warnings' in info:
            for module, warning in info['warnings'].items():
                if '*' in warning:
                    log.warning(warning['*'])

        if 'error' in info:
            if info['error'].get('code') in {'internal_api_error_DBConnectionError',
                                             'internal_api_error_DBQueryError'}:
                sleeper.sleep()
                return False

            # cope with https://phabricator.wikimedia.org/T106066
            if (
                info['error'].get('code') == 'mwoauth-invalid-authorization'
                and 'Nonce already used' in info['error'].get('info')
            ):
                log.warning('Retrying due to nonce error, see'
                            'https://phabricator.wikimedia.org/T106066')
                sleeper.sleep()
                return False

            if 'query' in info['error']:
                # Semantic Mediawiki does not follow the standard error format
                raise errors.APIError(None, info['error']['query'], kwargs)

            if '*' in info['error']:
                raise errors.APIError(info['error']['code'],
                                      info['error']['info'], info['error']['*'])
            raise errors.APIError(info['error']['code'],
                                  info['error']['info'], kwargs)
        return True

    @staticmethod
    def _query_string(*args, **kwargs):
        kwargs.update(args)
        qs1 = [
            (k, v) for k, v in kwargs.items() if k not in {'wpEditToken', 'token'}
        ]
        qs2 = [
            (k, v) for k, v in kwargs.items() if k in {'wpEditToken', 'token'}
        ]
        return OrderedDict(qs1 + qs2)

    def raw_call(self, script, data, files=None, retry_on_error=True, http_method='POST'):
        """
        Perform a generic request and return the raw text.

        In the event of a network problem, or an HTTP response with status code 5XX,
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
            http_method (str): The HTTP method, defaults to 'POST'

        Returns:
            The raw text response.

        Raises:
            errors.MaximumRetriesExceeded: The API request failed and the maximum number
                of retries was exceeded.
            requests.exceptions.HTTPError: Received an invalid HTTP response, or a status
                code in the 4xx range.
            requests.exceptions.ConnectionError: Encountered an unexpected error while
                performing the API request.
            requests.exceptions.Timeout: The API request timed out.
        """
        headers = {}
        if self.compress:
            headers['Accept-Encoding'] = 'gzip'
        sleeper = self.sleepers.make((script, data))

        scheme = self.scheme
        host = self.host
        if isinstance(host, (list, tuple)):
            warnings.warn(
                'Specifying host as a tuple is deprecated as of mwclient 0.10.1. '
                + 'Please use the new scheme argument instead.',
                DeprecationWarning
            )
            scheme, host = host

        url = '{scheme}://{host}{path}{script}{ext}'.format(scheme=scheme, host=host,
                                                            path=self.path, script=script,
                                                            ext=self.ext)

        while True:
            toraise = None
            wait_time = 0
            args = {'files': files, 'headers': headers}
            for k, v in self.requests.items():
                args[k] = v
            if http_method == 'GET':
                args['params'] = data
            else:
                args['data'] = data

            try:
                stream = self.connection.request(http_method, url, **args)
                if stream.headers.get('x-database-lag'):
                    wait_time = int(stream.headers.get('retry-after'))
                    log.warning('Database lag exceeds max lag. '
                                'Waiting for {} seconds'.format(wait_time))
                    # fall through to the sleep
                elif stream.status_code == 200:
                    return stream.text
                elif stream.status_code < 500 or stream.status_code > 599:
                    stream.raise_for_status()
                else:
                    if not retry_on_error:
                        stream.raise_for_status()
                    log.warning('Received {status} response: {text}. '
                                'Retrying in a moment.'
                                .format(status=stream.status_code,
                                        text=stream.text))
                    toraise = "stream"
                    # fall through to the sleep

            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout
            ) as err:
                # In the event of a network problem
                # (e.g. DNS failure, refused connection, etc),
                # Requests will raise a ConnectionError exception.
                if not retry_on_error:
                    raise
                log.warning('Connection error. Retrying in a moment.')
                toraise = err
                # proceed to the sleep

            # all retry paths come here
            try:
                sleeper.sleep(wait_time)
            except errors.MaximumRetriesExceeded:
                if toraise == "stream":
                    stream.raise_for_status()
                elif toraise:
                    raise toraise
                else:
                    raise

    def raw_api(self, action, http_method='POST', retry_on_error=True, *args, **kwargs):
        """Send a call to the API.

        Args:
            action (str): The MediaWiki API action to perform.
            http_method (str): The HTTP method to use in the request.
            retry_on_error (bool): Whether to retry API call on connection errors.
            *args (Tuple[str, Any]): Arguments to be passed to the `api.php` script as
                data.
            **kwargs (Any): Arguments to be passed to the `api.php` script as data.

        Returns:
            The API response.

        Raises:
            errors.APIDisabledError: The MediaWiki API is disabled for this instance.
            errors.InvalidResponse: The API response could not be decoded from JSON.
            errors.MaximumRetriesExceeded: The API request failed and the maximum number
                of retries was exceeded.
            requests.exceptions.HTTPError: Received an invalid HTTP response, or a status
                code in the 4xx range.
            requests.exceptions.ConnectionError: Encountered an unexpected error while
                performing the API request.
            requests.exceptions.Timeout: The API request timed out.
        """
        kwargs['action'] = action
        kwargs['format'] = 'json'
        data = self._query_string(*args, **kwargs)
        res = self.raw_call('api', data, retry_on_error=retry_on_error,
                            http_method=http_method)

        try:
            return json.loads(res, object_pairs_hook=OrderedDict)
        except ValueError:
            if res.startswith('MediaWiki API is not enabled for this site.'):
                raise errors.APIDisabledError
            raise errors.InvalidResponse(res)

    def raw_index(self, action, http_method='POST', *args, **kwargs):
        """Sends a call to index.php rather than the API.

        Args:
            action (str): The MediaWiki API action to perform.
            http_method (str): The HTTP method to use in the request.
            *args (Tuple[str, Any]): Arguments to be passed to the `index.php` script as
                data.
            **kwargs (Any): Arguments to be passed to the `index.php` script as data.

        Returns:
            The API response.

        Raises:
            errors.MaximumRetriesExceeded: The API request failed and the maximum number
                of retries was exceeded.
            requests.exceptions.HTTPError: Received an invalid HTTP response, or a status
                code in the 4xx range.
            requests.exceptions.ConnectionError: Encountered an unexpected error while
                performing the API request.
            requests.exceptions.Timeout: The API request timed out.
        """
        kwargs['action'] = action
        kwargs['maxlag'] = self.max_lag
        data = self._query_string(*args, **kwargs)
        return self.raw_call('index', data, http_method=http_method)

    def require(self, major, minor, revision=None, raise_error=True):
        """Check whether the current wiki matches the required version.

        Args:
            major (int): The required major version.
            minor (int): The required minor version.
            revision (int): The required revision.
            raise_error (bool): Whether to throw an error if the version of the current
                wiki is below the required version. Defaults to `True`.

        Returns:
            `False` if the version of the current wiki is below the required version, else
                `True`. If either `raise_error=True` or the site is uninitialized and
                `raise_error=None` then nothing is returned.

        Raises:
            errors.MediaWikiVersionError: The current wiki is below the required version
                and `raise_error=True`.
            RuntimeError: It `raise_error` is `None` and the `version` attribute is unset
                This is usually done automatically on construction of the :class:`Site`,
                unless `do_init=False` is passed to the constructor. After instantiation,
                the :meth:`~Site.site_init` functon can be used to retrieve and set the
                `version`.
            NotImplementedError: If the `revision` argument was passed. The logic for this
                is currently unimplemented.
        """
        if self.version is None:
            if raise_error is None:
                return
            # FIXME: Replace this with a specific error
            raise RuntimeError('Site %s has not yet been initialized' % repr(self))

        if revision is None:
            if self.version[:2] >= (major, minor):
                return True
            elif raise_error:
                raise errors.MediaWikiVersionError(
                    'Requires version {required[0]}.{required[1]}, '
                    'current version is {current[0]}.{current[1]}'
                    .format(required=(major, minor),
                            current=(self.version[:2]))
                )
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
            ... except mwclient.errors.NoSpecifiedEmail:
            ...     print('User does not accept email, or has no email address.')

        Args:
            user (str): User name of the recipient
            text (str): Body of the email
            subject (str): Subject of the email
            cc (bool): True to send a copy of the email to yourself (default is False)

        Returns:
            Dictionary of the JSON response

        Raises:
            NoSpecifiedEmail (mwclient.errors.NoSpecifiedEmail): User doesn't accept email
            EmailError (mwclient.errors.EmailError): Other email errors
        """

        token = self.get_token('email')

        try:
            info = self.post('emailuser', target=user, subject=subject,
                             text=text, ccme=cc, token=token)
        except errors.APIError as e:
            if e.args[0] == 'noemail':
                raise errors.NoSpecifiedEmail(user, e.args[1])
            raise errors.EmailError(*e)

        return info

    def login(self, username=None, password=None, cookies=None, domain=None):
        """
        Login to the wiki using a username and bot password. The method returns
        nothing if the login was successful, but raises and error if it was not.
        If you use mediawiki >= 1.27 and try to login with normal account
        (not botpassword account), you should use `clientlogin` instead, because login
        action is deprecated since 1.27 with normal account and will stop
        working in the near future. See these pages to learn more:
            - https://www.mediawiki.org/wiki/API:Login and
            - https://www.mediawiki.org/wiki/Manual:Bot_passwords

        Note: at least until v1.33.1, botpasswords accounts seem to not have
              "userrights" permission. If you need to update user's groups,
              this permission is required so you must use `client login`
              with a user who has userrights permission (a bureaucrat for eg.).

        Args:
            username (str): MediaWiki username
            password (str): MediaWiki password
            cookies (dict): Custom cookies to include with the log-in request.
            domain (str): Sends domain name for authentication; used by some
                MediaWiki plug-ins like the 'LDAP Authentication' extension.

        Raises:
            LoginError (mwclient.errors.LoginError): Login failed, the reason can be
                obtained from e.code and e.info (where e is the exception object) and
                will be one of the API:Login errors. The most common error code is
                "Failed", indicating a wrong username or password.

            MaximumRetriesExceeded: API call to log in failed and was retried until all
                retries were exhausted. This will not occur if the credentials are merely
                incorrect. See MaximumRetriesExceeded for possible reasons.

            APIError: An API error occurred. Rare, usually indicates an internal server
                error.
        """

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

            # Try to login using the scheme for MW 1.27+. If the wiki is read protected,
            # it is not possible to get the wiki version upfront using the API, so we just
            # have to try. If the attempt fails, we try the old method.
            try:
                kwargs['lgtoken'] = self.get_token('login')
            except (errors.APIError, KeyError):
                log.debug('Failed to get login token, MediaWiki is older than 1.27.')

            while True:
                login = self.post('login', **kwargs)

                if login['login']['result'] == 'Success':
                    break
                elif login['login']['result'] == 'NeedToken':
                    kwargs['lgtoken'] = login['login']['token']
                elif login['login']['result'] == 'Throttled':
                    sleeper.sleep(int(login['login'].get('wait', 5)))
                else:
                    raise errors.LoginError(self, login['login']['result'],
                                            login['login']['reason'])

        self.site_init()

    def clientlogin(self, cookies=None, **kwargs):
        """
        Login to the wiki using a username and password. The method returns
        True if it's a success or the returned response if it's a multi-steps
        login process you started. In case of failure it raises some Errors.

        Example for classic username / password clientlogin request:
            >>> try:
            ...     site.clientlogin(username='myusername', password='secret')
            ... except mwclient.errors.LoginError as e:
            ...     print('Could not login to MediaWiki: %s' % e)

        Args:
            cookies (dict): Custom cookies to include with the log-in request.
            **kwargs (dict): Custom vars used for clientlogin as:
                - loginmergerequestfields
                - loginpreservestate
                - loginreturnurl,
                - logincontinue
                - logintoken
                - *: additional params depending on the available auth requests.
                     to log with classic username / password, you need to add
                     `username` and `password`
                See https://www.mediawiki.org/wiki/API:Login#Method_2._clientlogin

        Raises:
            LoginError (mwclient.errors.LoginError): Login failed, the reason can be
                obtained from e.code and e.info (where e is the exception object) and
                will be one of the API:Login errors. The most common error code is
                "Failed", indicating a wrong username or password.

            MaximumRetriesExceeded: API call to log in failed and was retried until all
                retries were exhausted. This will not occur if the credentials are merely
                incorrect. See MaximumRetriesExceeded for possible reasons.

            APIError: An API error occurred. Rare, usually indicates an internal server
                error.
        """

        self.require(1, 27)

        if cookies:
            self.connection.cookies.update(cookies)

        if kwargs:
            # Try to login using the scheme for MW 1.27+. If the wiki is read protected,
            # it is not possible to get the wiki version upfront using the API, so we just
            # have to try. If the attempt fails, we try the old method.
            if 'logintoken' not in kwargs:
                try:
                    kwargs['logintoken'] = self.get_token('login')
                except (errors.APIError, KeyError):
                    log.debug('Failed to get login token, MediaWiki is older than 1.27.')

            if 'logincontinue' not in kwargs and 'loginreturnurl' not in kwargs:
                # should be great if API didn't require this...
                kwargs['loginreturnurl'] = '%s://%s' % (self.scheme, self.host)

            while True:
                login = self.post('clientlogin', **kwargs)
                status = login['clientlogin'].get('status')
                if status == 'PASS':
                    return True
                elif status in ('UI', 'REDIRECT'):
                    return login['clientlogin']
                else:
                    raise errors.LoginError(self, status,
                                            login['clientlogin'].get('message'))

    def get_token(self, type, force=False, title=None):
        """Request a MediaWiki access token of the given `type`.

        Args:
            type (str): The type of token to request.
            force (bool): Force the request of a new token, even if a token of that type
                has already been cached.
            title (str): The page title for which to request a token. Only used for
                MediaWiki versions below 1.24.

        Returns:
            A MediaWiki token of the requested `type`.

        Raises:
            errors.APIError: A token of the given type could not be retrieved.
        """
        if self.version is None or self.version[:2] >= (1, 24):
            # The 'csrf' (cross-site request forgery) token introduced in 1.24 replaces
            # the majority of older tokens, like edittoken and movetoken.
            if type not in {'watch', 'patrol', 'rollback', 'userrights', 'login'}:
                type = 'csrf'

        if type not in self.tokens:
            self.tokens[type] = '0'

        if self.tokens.get(type, '0') == '0' or force:

            if self.version is None or self.version[:2] >= (1, 24):
                # We use raw_api() rather than api() because api() is adding "userinfo"
                # to the query and this raises a readapideniederror if the wiki is read
                # protected, and we're trying to fetch a login token.
                info = self.raw_api('query', 'GET', meta='tokens', type=type)

                self.handle_api_result(info)

                # Note that for read protected wikis, we don't know the version when
                # fetching the login token. If it's < 1.27, the request below will
                # raise a KeyError that we should catch.
                self.tokens[type] = info['query']['tokens']['%stoken' % type]

            else:
                if title is None:
                    # Some dummy title was needed to get a token prior to 1.24
                    title = 'Test'
                info = self.post('query', titles=title,
                                 prop='info', intoken=type)
                for i in info['query']['pages'].values():
                    if i['title'] == title:
                        self.tokens[type] = i['%stoken' % type]

        return self.tokens[type]

    def upload(self, file=None, filename=None, description='', ignore=False,
               file_size=None, url=None, filekey=None, comment=None):
        """Upload a file to the site.

        Note that one of `file`, `filekey` and `url` must be specified, but not
        more than one. For normal uploads, you specify `file`.

        Args:
            file (str): File object or stream to upload.
            filename (str): Destination filename, don't include namespace
                            prefix like 'File:'
            description (str): Wikitext for the file description page.
            ignore (bool): True to upload despite any warnings.
            file_size (int): Deprecated in mwclient 0.7
            url (str): URL to fetch the file from.
            filekey (str): Key that identifies a previous upload that was
                           stashed temporarily.
            comment (str): Upload comment. Also used as the initial page text
                           for new files if `description` is not specified.

        Example:

            >>> client.upload(open('somefile', 'rb'), filename='somefile.jpg',
                              description='Some description')

        Returns:
            JSON result from the API.

        Raises:
            errors.InsufficientPermission
            requests.exceptions.HTTPError
            errors.FileExists: The file already exists and `ignore` is `False`.
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
            raise TypeError(
                "exactly one of 'file', 'filekey' and 'url' must be specified"
            )

        image = self.Images[filename]
        if not image.can('upload'):
            raise errors.InsufficientPermission(filename)

        if comment is None:
            comment = description
            text = None
        else:
            comment = comment
            text = description

        if file is not None:
            if not hasattr(file, 'read'):
                file = open(file, 'rb')

            content_size = file.seek(0, 2)
            file.seek(0)

            if self.version[:2] >= (1, 20) and content_size > self.chunk_size:
                return self.chunk_upload(file, filename, ignore, comment, text)

        predata = {
            'action': 'upload',
            'format': 'json',
            'filename': filename,
            'comment': comment,
            'text': text,
            'token': image.get_token('edit'),
        }

        if ignore:
            predata['ignorewarnings'] = 'true'
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
            files = {'file': ('fake-filename', file)}

        sleeper = self.sleepers.make()
        while True:
            data = self.raw_call('api', postdata, files)
            info = json.loads(data)
            if not info:
                info = {}
            if self.handle_api_result(info, kwargs=predata, sleeper=sleeper):
                response = info.get('upload', {})
                # Workaround for https://github.com/mwclient/mwclient/issues/211
                # ----------------------------------------------------------------
                # Raise an error if the file already exists. This is necessary because
                # MediaWiki returns a warning, not an error, leading to silent failure.
                # The user must explicitly set ignore=True (ignorewarnings=True) to
                # overwrite an existing file.
                if ignore is False and 'exists' in response.get('warnings', {}):
                    raise errors.FileExists(filename)
                break

        if file is not None:
            file.close()
        return response

    def chunk_upload(self, file, filename, ignorewarnings, comment, text):
        """Upload a file to the site in chunks.

        This method is called by `Site.upload` if you are connecting to a newer
        MediaWiki installation, so it's normally not necessary to call this
        method directly.

        Args:
            file (file-like object): File object or stream to upload.
            params (dict): Dict containing upload parameters.
        """
        image = self.Images[filename]

        content_size = file.seek(0, 2)
        file.seek(0)

        params = {
            'action': 'upload',
            'format': 'json',
            'stash': 1,
            'offset': 0,
            'filename': filename,
            'filesize': content_size,
            'token': image.get_token('edit'),
        }
        if ignorewarnings:
            params['ignorewarnings'] = 'true'

        sleeper = self.sleepers.make()
        offset = 0
        for chunk in read_in_chunks(file, self.chunk_size):
            while True:
                data = self.raw_call('api', params, files={'chunk': chunk})
                info = json.loads(data)
                if self.handle_api_result(info, kwargs=params, sleeper=sleeper):
                    response = info.get('upload', {})
                    break

            offset += chunk.tell()
            chunk.close()
            log.debug('%s: Uploaded %d of %d bytes', filename, offset, content_size)
            params['filekey'] = response['filekey']
            if response['result'] == 'Continue':
                params['offset'] = response['offset']
            elif response['result'] == 'Success':
                file.close()
                break
            else:
                # Some kind or error or warning occurred. In any case, we do not
                # get the parameters we need to continue, so we should return
                # the response now.
                file.close()
                return response

        del params['action']
        del params['stash']
        del params['offset']
        params['comment'] = comment
        params['text'] = text
        return self.post('upload', **params)

    def parse(self, text=None, title=None, page=None, prop=None,
              redirects=False, mobileformat=False):
        """Parses the given content and returns parser output.

        Args:
            text (str): Text to parse.
            title (str): Title of page the text belongs to.
            page (str): The name of a page to parse. Cannot be used together with text
                and title.
            prop (str): Which pieces of information to get. Multiple alues should be
                separated using the pipe (`|`) character.
            redirects (bool): Resolve the redirect, if the given `page` is a redirect.
                Defaults to `False`.
            mobileformat (bool): Return parse output in a format suitable for mobile
                devices. Defaults to `False`.

        Returns:
            The parse output as generated by MediaWiki.
        """
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
        result = self.post('parse', **kwargs)
        return result['parse']

    # def block(self): TODO?
    # def unblock: TODO?
    # def import: TODO?

    def patrol(self, rcid=None, revid=None, tags=None):
        """Patrol a page or a revision. Either ``rcid`` or ``revid`` (but not both) must
        be given.
        The ``rcid`` and ``revid`` arguments may be obtained using the
        :meth:`Site.recentchanges` function.

        API doc: https://www.mediawiki.org/wiki/API:Patrol

        Args:
            rcid (int): The recentchanges ID to patrol.
            revid (int): The revision ID to patrol.
            tags (str): Change tags to apply to the entry in the patrol log. Multiple
                tags can be given, by separating them with the pipe (|) character.

        Returns:
            Dict[str, Any]: The API response as a dictionary containing:

            - **rcid** (int): The recentchanges id.
            - **nsid** (int): The namespace id.
            - **title** (str): The page title.

        Raises:
            errors.APIError: The MediaWiki API returned an error.

        Notes:
            - ``autopatrol`` rights are required in order to use this function.
            - ``revid`` requires at least MediaWiki 1.22.
            - ``tags`` requires at least MediaWiki 1.27.
        """
        if self.require(1, 17, raise_error=False):
            token = self.get_token('patrol')
        else:
            # For MediaWiki versions earlier than 1.17, the patrol token is the same the
            # edit token.
            token = self.get_token('edit')

        result = self.post('patrol', rcid=rcid, revid=revid, tags=tags, token=token)
        return result['patrol']

    # Lists
    def allpages(self, start=None, prefix=None, namespace='0', filterredir='all',
                 minsize=None, maxsize=None, prtype=None, prlevel=None,
                 limit=None, dir='ascending', filterlanglinks='all', generator=True,
                 end=None, max_items=None, api_chunk_size=None):
        """Retrieve all pages on the wiki as a generator."""

        (max_items, api_chunk_size) = handle_limit(limit, max_items, api_chunk_size)
        pfx = listing.List.get_prefix('ap', generator)
        kwargs = dict(listing.List.generate_kwargs(
            pfx, ('from', start), ('to', end), prefix=prefix,
            minsize=minsize, maxsize=maxsize, prtype=prtype, prlevel=prlevel,
            namespace=namespace, filterredir=filterredir, dir=dir,
            filterlanglinks=filterlanglinks,
        ))
        return listing.List.get_list(generator)(self, 'allpages', 'ap',
                                                max_items=max_items,
                                                api_chunk_size=api_chunk_size,
                                                return_values='title',
                                                **kwargs)

    def allimages(self, start=None, prefix=None, minsize=None, maxsize=None, limit=None,
                  dir='ascending', sha1=None, sha1base36=None, generator=True, end=None,
                  max_items=None, api_chunk_size=None):
        """Retrieve all images on the wiki as a generator."""

        (max_items, api_chunk_size) = handle_limit(limit, max_items, api_chunk_size)
        pfx = listing.List.get_prefix('ai', generator)
        kwargs = dict(listing.List.generate_kwargs(
            pfx, ('from', start), ('to', end), prefix=prefix,
            minsize=minsize, maxsize=maxsize,
            dir=dir, sha1=sha1, sha1base36=sha1base36,
        ))
        return listing.List.get_list(generator)(self, 'allimages', 'ai',
                                                max_items=max_items,
                                                api_chunk_size=api_chunk_size,
                                                return_values='timestamp|url',
                                                **kwargs)

    def alllinks(self, start=None, prefix=None, unique=False, prop='title',
                 namespace='0', limit=None, generator=True, end=None, max_items=None,
                 api_chunk_size=None):
        """Retrieve a list of all links on the wiki as a generator."""

        (max_items, api_chunk_size) = handle_limit(limit, max_items, api_chunk_size)
        pfx = listing.List.get_prefix('al', generator)
        kwargs = dict(listing.List.generate_kwargs(pfx, ('from', start), ('to', end),
                                                   prefix=prefix,
                                                   prop=prop, namespace=namespace))
        if unique:
            kwargs[pfx + 'unique'] = '1'
        return listing.List.get_list(generator)(self, 'alllinks', 'al',
                                                max_items=max_items,
                                                api_chunk_size=api_chunk_size,
                                                return_values='title', **kwargs)

    def allcategories(self, start=None, prefix=None, dir='ascending', limit=None,
                      generator=True, end=None, max_items=None, api_chunk_size=None):
        """Retrieve all categories on the wiki as a generator."""

        (max_items, api_chunk_size) = handle_limit(limit, max_items, api_chunk_size)
        pfx = listing.List.get_prefix('ac', generator)
        kwargs = dict(listing.List.generate_kwargs(pfx, ('from', start), ('to', end),
                                                   prefix=prefix, dir=dir))
        return listing.List.get_list(generator)(self, 'allcategories', 'ac',
                                                max_items=max_items,
                                                api_chunk_size=api_chunk_size, **kwargs)

    def allusers(self, start=None, prefix=None, group=None, prop=None, limit=None,
                 witheditsonly=False, activeusers=False, rights=None, end=None,
                 max_items=None, api_chunk_size=None):
        """Retrieve all users on the wiki as a generator."""

        (max_items, api_chunk_size) = handle_limit(limit, max_items, api_chunk_size)
        kwargs = dict(listing.List.generate_kwargs('au', ('from', start), ('to', end),
                                                   prefix=prefix,
                                                   group=group, prop=prop,
                                                   rights=rights,
                                                   witheditsonly=witheditsonly,
                                                   activeusers=activeusers))
        return listing.List(self, 'allusers', 'au', max_items=max_items,
                            api_chunk_size=api_chunk_size, **kwargs)

    def blocks(self, start=None, end=None, dir='older', ids=None, users=None, limit=None,
               prop='id|user|by|timestamp|expiry|reason|flags', max_items=None,
               api_chunk_size=None):
        """Retrieve blocks as a generator.

        API doc: https://www.mediawiki.org/wiki/API:Blocks

        Returns:
            mwclient.listings.List: Generator yielding dicts, each dict containing:
                - user: The username or IP address of the user
                - id: The ID of the block
                - timestamp: When the block was added
                - expiry: When the block runs out (infinity for indefinite blocks)
                - reason: The reason they are blocked
                - allowusertalk: Key is present (empty string) if the user is allowed to
                    edit their user talk page
                - by: the administrator who blocked the user
                - nocreate: key is present (empty string) if the user's ability to create
                    accounts has been disabled.

        See Also:
            When using the ``users`` filter to search for blocked users, only one block
            per given user will be returned. If you want to retrieve the entire block log
            for a specific user, you can use the :meth:`Site.logevents` method with
            ``type=block`` and ``title='User:JohnDoe'``.
        """

        # TODO: Fix. Fix what?
        (max_items, api_chunk_size) = handle_limit(limit, max_items, api_chunk_size)
        kwargs = dict(listing.List.generate_kwargs('bk', start=start, end=end, dir=dir,
                                                   ids=ids, users=users, prop=prop))
        return listing.List(self, 'blocks', 'bk', max_items=max_items,
                            api_chunk_size=api_chunk_size, **kwargs)

    def deletedrevisions(self, start=None, end=None, dir='older', namespace=None,
                         limit=None, prop='user|comment', max_items=None,
                         api_chunk_size=None):
        # TODO: Fix
        (max_items, api_chunk_size) = handle_limit(limit, max_items, api_chunk_size)
        kwargs = dict(listing.List.generate_kwargs('dr', start=start, end=end, dir=dir,
                                                   namespace=namespace, prop=prop))
        return listing.List(self, 'deletedrevs', 'dr', max_items=max_items,
                            api_chunk_size=api_chunk_size, **kwargs)

    def exturlusage(self, query, prop=None, protocol='http', namespace=None, limit=None,
                    max_items=None, api_chunk_size=None):
        r"""Retrieve the list of pages that link to a particular domain or URL,
         as a generator.

        This API call mirrors the Special:LinkSearch function on-wiki.

        Query can be a domain like 'bbc.co.uk'.
        Wildcards can be used, e.g. '\*.bbc.co.uk'.
        Alternatively, a query can contain a full domain name and some or all of a URL:
        e.g. '\*.wikipedia.org/wiki/\*'

        See <https://meta.wikimedia.org/wiki/Help:Linksearch> for details.

        Returns:
            mwclient.listings.List: Generator yielding dicts, each dict containing:
                - url: The URL linked to.
                - ns: Namespace of the wiki page
                - pageid: The ID of the wiki page
                - title: The page title.

        """

        (max_items, api_chunk_size) = handle_limit(limit, max_items, api_chunk_size)
        kwargs = dict(listing.List.generate_kwargs('eu', query=query, prop=prop,
                                                   protocol=protocol,
                                                   namespace=namespace))
        return listing.List(self, 'exturlusage', 'eu', max_items=max_items,
                            api_chunk_size=api_chunk_size, **kwargs)

    def logevents(self, type=None, prop=None, start=None, end=None,
                  dir='older', user=None, title=None, limit=None, action=None,
                  max_items=None, api_chunk_size=None):
        """Retrieve logevents as a generator."""
        (max_items, api_chunk_size) = handle_limit(limit, max_items, api_chunk_size)
        kwargs = dict(listing.List.generate_kwargs('le', prop=prop, type=type,
                                                   start=start, end=end, dir=dir,
                                                   user=user, title=title, action=action))
        return listing.List(self, 'logevents', 'le', max_items=max_items,
                            api_chunk_size=api_chunk_size, **kwargs)

    def checkuserlog(self, user=None, target=None, limit=None, dir='older',
                     start=None, end=None, max_items=None, api_chunk_size=10):
        """Retrieve checkuserlog items as a generator."""

        (max_items, api_chunk_size) = handle_limit(limit, max_items, api_chunk_size)
        kwargs = dict(listing.List.generate_kwargs('cul', target=target, start=start,
                                                   end=end, dir=dir, user=user))
        return listing.NestedList('entries', self, 'checkuserlog', 'cul',
                                  max_items=max_items, api_chunk_size=api_chunk_size,
                                  **kwargs)

    # def protectedtitles requires 1.15
    def random(self, namespace, limit=None, max_items=None, api_chunk_size=20):
        """Retrieve a generator of random pages from a particular namespace.

        max_items specifies the number of random articles retrieved.
        api_chunk_size and limit (deprecated) specify the API chunk size.
        namespace is a namespace identifier integer.

        Generator contains dictionary with namespace, page ID and title.

        """

        (max_items, api_chunk_size) = handle_limit(limit, max_items, api_chunk_size)
        kwargs = dict(listing.List.generate_kwargs('rn', namespace=namespace))
        return listing.List(self, 'random', 'rn', max_items=max_items,
                            api_chunk_size=api_chunk_size, **kwargs)

    def recentchanges(self, start=None, end=None, dir='older', namespace=None,
                      prop=None, show=None, limit=None, type=None, toponly=None,
                      max_items=None, api_chunk_size=None):
        """List recent changes to the wiki, à la Special:Recentchanges.
        """
        (max_items, api_chunk_size) = handle_limit(limit, max_items, api_chunk_size)
        kwargs = dict(listing.List.generate_kwargs('rc', start=start, end=end, dir=dir,
                                                   namespace=namespace, prop=prop,
                                                   show=show, type=type,
                                                   toponly='1' if toponly else None))
        return listing.List(self, 'recentchanges', 'rc', max_items=max_items,
                            api_chunk_size=api_chunk_size, **kwargs)

    def revisions(self, revids, prop='ids|timestamp|flags|comment|user'):
        """Get data about a list of revisions.

        See also the `Page.revisions()` method.

        API doc: https://www.mediawiki.org/wiki/API:Revisions

        Example: Get revision text for two revisions:

            >>> for revision in site.revisions([689697696, 689816909], prop='content'):
            ...     print(revision['*'])

        Args:
            revids (list): A list of (max 50) revisions.
            prop (str): Which properties to get for each revision.

        Returns:
            A list of revisions
        """
        kwargs = {
            'prop': 'revisions',
            'rvprop': prop,
            'revids': '|'.join(map(str, revids))
        }

        revisions = []
        pages = self.get('query', **kwargs).get('query', {}).get('pages', {}).values()
        for page in pages:
            for revision in page.get('revisions', ()):
                revision['pageid'] = page.get('pageid')
                revision['pagetitle'] = page.get('title')
                revision['timestamp'] = parse_timestamp(revision['timestamp'])
                revisions.append(revision)
        return revisions

    def search(self, search, namespace='0', what=None, redirects=False, limit=None,
               max_items=None, api_chunk_size=None):
        """Perform a full text search.

        API doc: https://www.mediawiki.org/wiki/API:Search

        Example:
            >>> for result in site.search('prefix:Template:Citation/'):
            ...     print(result.get('title'))

        Args:
            search (str): The query string
            namespace (int): The namespace to search (default: 0)
            what (str): Search scope: 'text' for fulltext, or 'title' for titles only.
                        Depending on the search backend,
                        both options may not be available.
                        For instance
                        `CirrusSearch <https://www.mediawiki.org/wiki/Help:CirrusSearch>`_
                        doesn't support 'title', but instead provides an "intitle:"
                        query string filter.
            redirects (bool): Include redirect pages in the search
                              (option removed in MediaWiki 1.23).

        Returns:
            mwclient.listings.List: Search results iterator
        """
        (max_items, api_chunk_size) = handle_limit(limit, max_items, api_chunk_size)
        kwargs = dict(listing.List.generate_kwargs('sr', search=search,
                                                   namespace=namespace, what=what))
        if redirects:
            kwargs['srredirects'] = '1'
        return listing.List(self, 'search', 'sr', max_items=max_items,
                            api_chunk_size=api_chunk_size, **kwargs)

    def usercontributions(self, user, start=None, end=None, dir='older', namespace=None,
                          prop=None, show=None, limit=None, uselang=None, max_items=None,
                          api_chunk_size=None):
        """
        List the contributions made by a given user to the wiki.

        API doc: https://www.mediawiki.org/wiki/API:Usercontribs
        """
        (max_items, api_chunk_size) = handle_limit(limit, max_items, api_chunk_size)
        kwargs = dict(listing.List.generate_kwargs('uc', user=user, start=start, end=end,
                                                   dir=dir, namespace=namespace,
                                                   prop=prop, show=show))
        return listing.List(self, 'usercontribs', 'uc', max_items=max_items,
                            api_chunk_size=api_chunk_size, uselang=uselang, **kwargs)

    def users(self, users, prop='blockinfo|groups|editcount'):
        """
        Get information about a list of users.

        API doc: https://www.mediawiki.org/wiki/API:Users
        """

        return listing.List(self, 'users', 'us', ususers='|'.join(users), usprop=prop)

    def watchlist(self, allrev=False, start=None, end=None, namespace=None, dir='older',
                  prop=None, show=None, limit=None, max_items=None, api_chunk_size=None):
        """
        List the pages on the current user's watchlist.

        API doc: https://www.mediawiki.org/wiki/API:Watchlist
        """

        (max_items, api_chunk_size) = handle_limit(limit, max_items, api_chunk_size)
        kwargs = dict(listing.List.generate_kwargs('wl', start=start, end=end,
                                                   namespace=namespace, dir=dir,
                                                   prop=prop, show=show))
        if allrev:
            kwargs['wlallrev'] = '1'
        return listing.List(self, 'watchlist', 'wl', max_items=max_items,
                            api_chunk_size=api_chunk_size, **kwargs)

    def expandtemplates(self, text, title=None, generatexml=False):
        """
        Takes wikitext (text) and expands templates.

        API doc: https://www.mediawiki.org/wiki/API:Expandtemplates

        Args:
            text (str): Wikitext to convert.
            title (str): Title of the page.
            generatexml (bool): Generate the XML parse tree. Defaults to `False`.
        """

        kwargs = {}
        if title is not None:
            kwargs['title'] = title
        if generatexml:
            # FIXME: Deprecated and replaced by `prop=parsetree`.
            kwargs['generatexml'] = '1'

        result = self.post('expandtemplates', text=text, **kwargs)

        if generatexml:
            return result['expandtemplates']['*'], result['parsetree']['*']
        else:
            return result['expandtemplates']['*']

    def ask(self, query, title=None):
        """
        Ask a query against Semantic MediaWiki.

        API doc: https://semantic-mediawiki.org/wiki/Ask_API

        Args:
            query (str): The SMW query to be executed.

        Returns:
            Generator for retrieving all search results, with each answer as a dictionary.
            If the query is invalid, an APIError is raised. A valid query with zero
            results will not raise any error.

        Examples:

            >>> query = "[[Category:my cat]]|[[Has name::a name]]|?Has property"
            >>> for answer in site.ask(query):
            >>>     for title, data in answer.items()
            >>>         print(title)
            >>>         print(data)
        """
        kwargs = {}
        if title is None:
            kwargs['title'] = title

        offset = 0
        while offset is not None:
            results = self.raw_api('ask', query='{query}|offset={offset}'.format(
                query=query, offset=offset), http_method='GET', **kwargs)
            self.handle_api_result(results)  # raises APIError on error
            offset = results.get('query-continue-offset')
            answers = results['query'].get('results', [])

            if isinstance(answers, dict):
                # In older versions of Semantic MediaWiki (at least until 2.3.0)
                # a list was returned. In newer versions an object is returned
                # with the page title as key.
                answers = [answer for answer in answers.values()]

            for answer in answers:
                yield answer
