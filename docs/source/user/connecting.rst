.. _`connecting`:

Connecting to your site
=======================

Begin by importing the Site class:

    >>> from mwclient import Site

Then try to connect to a site:

    >>> site = mwclient.Site('test.wikipedia.org')

By default, mwclient will connect using https. If your site doesn't support
https, you need to explicitly request http like so:

    >>> site = mwclient.Site(('http', 'test.wikipedia.org'))

.. _endpoint:

The API endpoint location
-------------------------

The API endpoint location on a MediaWiki site depends on the configurable
`$wgScriptPath`_. Mwclient defaults to the script path '/w/' used by the
Wikimedia wikis. If you get a 404 Not Found or a
:class:`mwclient.errors.InvalidResponse` error upon connecting, your site might
use a different script path. You can specify it using the ``path`` argument:

    >>> site = mwclient.Site('my-awesome-wiki.org', path='/wiki/', )

.. _$wgScriptPath: https://www.mediawiki.org/wiki/Manual:$wgScriptPath

.. _user-agent:

Specifying a user agent
-----------------------

If you are connecting to a Wikimedia site, you should follow the
`Wikimedia User-Agent policy`_ and identify your tool like so:

    >>> ua = 'MyCoolTool/0.2 run by User:Xyz'
    >>> site = mwclient.Site('test.wikipedia.org', clients_useragent=ua)

Note that Mwclient appends ' - MwClient/{version} ({url})' to your string.

.. _Wikimedia User-Agent policy: https://meta.wikimedia.org/wiki/User-Agent_policy

.. _auth:

Errors and warnings
-------------------

Deprecations and other warnings from the API are logged using the
`standard Python logging facility`_, so you can handle them in any way you like.
To print them to stdout:

    >>> import logging
    >>> logging.basicConfig(level=logging.WARNING)

.. _standard Python logging facility: https://docs.python.org/3/library/logging.html

Errors are thrown as exceptions. All exceptions inherit
:class:`mwclient.errors.MwClientError`.

Authenticating
--------------

Mwclient supports several methods for authentication described below. By default
it will also protect you from editing when not authenticated by raising a
:class:`mwclient.errors.LoginError`. If you actually *do* want to edit
unauthenticated, just set

    >>> site.force_login = False

.. _oauth:

OAuth
^^^^^

On Wikimedia wikis, the recommended authentication method is to authenticate as
a `owner-only consumer`_. Once you have obtained the *consumer token* (also
called *consumer key*), the *consumer secret*, the *access token* and the
*access secret*, you can authenticate like so:

    >>> site = mwclient.Site('test.wikipedia.org',
                             consumer_token='my_consumer_token',
                             consumer_secret='my_consumer_secret',
                             access_token='my_access_token',
                             access_secret='my_access_secret')


.. _owner-only consumer: https://www.mediawiki.org/wiki/OAuth/Owner-only_consumers
.. _old_login:

Old-school login
^^^^^^^^^^^^^^^^

To use old-school login, call the login method:

    >>> site.login('my_username', 'my_password')

If login fails, a :class:`mwclient.errors.LoginError` will be thrown.

.. _http-auth:

HTTP authentication
^^^^^^^^^^^^^^^^^^^

If your server is configured to use HTTP authentication, you can
authenticate using the ``httpauth`` parameter. For Basic HTTP authentication:

    >>> site = mwclient.Site('awesome.site', httpauth=('my_username', 'my_password'))

You can also pass in any other :ref:`authentication mechanism <requests:authentication>`
based on the :class:`requests.auth.AuthBase`, such as Digest authentication:

	>>> from requests.auth import HTTPDigestAuth
	>>> site = mwclient.Site('awesome.site', httpauth=HTTPDigestAuth('my_username', 'my_password'))

SSL client certificate authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If your server requires a SSL client certificate to authenticate, you can
pass the ``client_certificate`` parameter:

    >>> site = mwclient.Site('awesome.site', client_certificate='/path/to/client-and-key.pem')
    
This parameter being a proxy to :class:`requests`' cert_ parameter, you can also specify a tuple (certificate, key) like:

    >>> site = mwclient.Site('awesome.site', client_certificate=('client.pem', 'key.pem'))
    
Please note that the private key must not be encrypted.

  .. _cert: http://docs.python-requests.org/en/master/user/advanced/#ssl-cert-verification
