.. _`connecting`:

Connecting to your site
=======================

Begin by importing the Site class:

    >>> from mwclient import Site

Then try to connect to a site:

    >>> site = mwclient.Site('test.wikipedia.org')

.. _https:

Using HTTPS
-----------

If the site supports HTTPS, you can create a secure connection by passing
in a tupple like so:

    >>> site = mwclient.Site(('https', 'test.wikipedia.org'))

Note that HTTPS is planned to be the default for the next major version of mwclient.

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

    >>> ua = 'MyCoolTool. Run by User:Xyz. Using mwclient/0.8'
    >>> site = mwclient.Site('test.wikipedia.org', clients_useragent=ua)

.. _logging-in:

Logging in
----------

To login to the wiki:

    >>> site.login(username, password)

If login fails, a :class:`mwclient.errors.LoginError` will be thrown.

Note that mwclient by default will protect you from editing if you should
forget to login. If you actually want to edit without logging in, just set

    >>> site.force_login = False

and mwclient won't get in your way.

.. _http-auth:

HTTP authentication
-------------------

If your server is configured to use HTTP authentication, you can
authenticate using the ``httpauth`` parameter. For Basic HTTP authentication:

    >>> site = mwclient.Site('awesome.site', httpauth=('user', 'pass'))

You can also pass in any other :ref:`authentication mechanism <requests:authentication>`
based on the :class:`requests.auth.AuthBase`, such as Digest authentication:

	>>> from requests.auth import HTTPDigestAuth
	>>> site = mwclient.Site('awesome.site', httpauth=HTTPDigestAuth('user', 'pass'))

