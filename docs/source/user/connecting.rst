.. _`connecting`:

Connecting to your site
=======================

Begin by importing the Site class:

    >>> from mwclient import Site

Then try to connect to a site:

    >>> site = mwclient.Site('test.wikipedia.org')

By default, mwclient will try to conncet using https. If your site
doesn't support https, you need to explicitly ask for http like so:

    >>> site = mwclient.Site(('http', 'test.wikipedia.org'))


.. _endpoint:

The API endpoint location
-------------------------

The site's API endpoint location depends on the configurable `$wgScriptPath <https://www.mediawiki.org/wiki/Manual:$wgScriptPath>`_.
Mwclient defaults to the script path '/w/' used by the Wikimedia wikis.
If you get a 404 Not Found or a :class:`mwclient.errors.InvalidResponse` error upon connecting,
your site might use a different script path. You can specify it using the `path` argument:

    >>> site = mwclient.Site(('https', 'myawesomewiki.org'), path='/wiki/', )

.. _user-agent:

Specifying a user agent
-----------------------

If you are connecting to a Wikimedia site, you should follow the
`Wikimedia User-Agent policy <https://meta.wikimedia.org/wiki/User-Agent_policy>`_
and identify your tool like so:

    >>> ua = 'MyCoolTool. Run by User:Xyz. Using mwclient/' + mwclient.__ver__
    >>> site = mwclient.Site('test.wikipedia.org', clients_useragent=ua)

.. _auth:

Authenticating
--------------

Note that mwclient by default will protect you from editing when unauthenticated.
If you actually want to edit unauthenticated, set

    >>> site.force_login = False

.. _oauth:

OAuth
^^^^^

mwclient supports different ways of authenticating. On Wikimedia
wikis, the recommended way is now to use OAuth to authenticate as a
`owner-only consumer <https://www.mediawiki.org/wiki/OAuth/Owner-only_consumers#Python>`_.
Once you have obtained the *consumer token* (also called *consumer key*), the
*consumer secret*, the *access token* and the *access secret*, you can authenticate
like so:

    >>> site = mwclient.Site('test.wikipedia.org',
                             consumer_token='my_consumer_token',
                             consumer_secret='my_consumer_secret',
                             access_token='my_access_token',
                             access_secret='my_access_secret')

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

