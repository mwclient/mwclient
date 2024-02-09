.. _connecting:

Connecting to your site
=======================

To connect to a MediaWiki site, you need to create a :class:`~mwclient.client.Site`
object and pass it the hostname of the site you want to connect to. The hostname
should not include the protocol (http or https) or the path to the API endpoint
(see :ref:`endpoint`).

.. code-block:: python

    from mwclient import Site

    user_agent = 'MyCoolTool/0.2 (xyz@example.org)'
    site = Site('en.wikipedia.org', clients_useragent=user_agent)

.. warning::

    The ``clients_useragent`` parameter, while optional, is highly recommended
    and may be required by some sites, such as the Wikimedia wikis (e.g.
    Wikipedia). Requests without a user agent may be rejected or rate-limited
    by the site. See :ref:`user-agent` for more information.

By default, mwclient will connect using https. If your site doesn't support
https, you need to explicitly request http like so:

    >>> site = Site('test.wikipedia.org', scheme='http')

.. _endpoint:

The API endpoint location
-------------------------

The API endpoint location on a MediaWiki site depends on the configurable
`$wgScriptPath`_. Mwclient defaults to the script path '/w/' used by the
Wikimedia wikis. If you get a 404 Not Found or a
:class:`mwclient.errors.InvalidResponse` error upon connecting, your site might
use a different script path. You can specify it using the ``path`` argument:

    >>> site = Site('my-awesome-wiki.org', path='/wiki/')

.. _$wgScriptPath: https://www.mediawiki.org/wiki/Manual:$wgScriptPath

.. _user-agent:

Specifying a user agent
-----------------------

If you are connecting to a Wikimedia site, you should follow the
`Wikimedia User-Agent policy`_.
The user agent should contain the tool name, the tool version
and a way to contact you:

    >>> user_agent = 'MyCoolTool/0.2 (xyz@example.org)'
    >>> site = Site('test.wikipedia.org', clients_useragent=user_agent)

It should follow the pattern
``{tool_name}/{tool_version} ({contact})``. The contact info can also
be your user name and the tool version may be omitted:
``RudolphBot (User:Santa Claus)``.

Note that MwClient appends its own user agent to the end of your string.
The final user agent will look like this:

    >>> site.clients_useragent
    'MyCoolTool/0.2 (xyz@example.org) mwclient/0.8.0'

.. _Wikimedia User-Agent policy: https://meta.wikimedia.org/wiki/User-Agent_policy

.. _errors:

Using a proxy
-------------

If you need to use a proxy, you can configure the :class:`requests.Session`
using the `reqs` parameter of the :class:`~mwclient.client.Site`.

.. code-block:: python

    import mwclient

    proxies = {
      'http': 'http://10.10.1.10:3128',
      'https': 'http://10.10.1.10:1080',
    }
    site = mwclient.Site('en.wikipedia.org', reqs={"proxy": proxies})

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

.. _auth:

Authenticating
--------------

Mwclient supports several methods for authentication described below. By default
it will also protect you from editing when not authenticated by raising a
:class:`mwclient.errors.LoginError`. If you actually *do* want to edit
unauthenticated, just set

    >>> site.force_login = False

.. _oauth:

OAuth Authentication
^^^^^^^^^^^^^^^^^^^^

On Wikimedia wikis, the recommended authentication method is to authenticate as
a `owner-only consumer`_. Once you have obtained the *consumer token* (also
called *consumer key*), the *consumer secret*, the *access token* and the
*access secret*, you can authenticate like so:

    >>> site = Site('test.wikipedia.org',
                    consumer_token='my_consumer_token',
                    consumer_secret='my_consumer_secret',
                    access_token='my_access_token',
                    access_secret='my_access_secret')


.. _owner-only consumer: https://www.mediawiki.org/wiki/OAuth/Owner-only_consumers

.. _username-password:

Username-Password Authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. warning::
    Username-Password authentication is not recommended for Wikimedia wikis.
    See :ref:`oauth` for the recommended authentication method.

The easiest way to authenticate is to call :meth:`~mwclient.client.Site.login`
with your username and password. If login fails, a
:class:`mwclient.errors.LoginError` will be raised.

    >>> site.login('my_username', 'my_password')

.. _http-auth:

HTTP authentication
^^^^^^^^^^^^^^^^^^^

.. warning::
    HTTP authentication does not replace MediaWiki's built-in authentication
    system. It is used to protect access to the API, not to authenticate users.

If your server is configured to use HTTP authentication, you can authenticate
using the ``httpauth`` parameter. This parameter is a proxy to the
``auth`` parameter of :class:`requests.Session` and can be set to any class
that extends :class:`requests.auth.AuthBase`. For example, to use basic
authentication:

    >>> from requests.auth import HTTPBasicAuth
    >>> site = Site('awesome.site', httpauth=HTTPBasicAuth('my_username', 'my_password'))


.. _ssl-auth:

SSL client certificate authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If your server requires an SSL client certificate to authenticate, you can
pass the ``client_certificate`` parameter:

    >>> site = Site('awesome.site', client_certificate='/path/to/client-and-key.pem')

This parameter being a proxy to :class:`requests`' cert_ parameter, you can also specify a tuple (certificate, key) like:

    >>> site = Site('awesome.site', client_certificate=('client.pem', 'key.pem'))

Please note that the private key must not be encrypted.

  .. _cert: http://docs.python-requests.org/en/master/user/advanced/#ssl-cert-verification

.. _logout:

Logging out
^^^^^^^^^^^

There is no logout method because merely exiting the script deletes all cookies, achieving the same effect.
