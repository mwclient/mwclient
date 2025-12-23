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

    >>> site.connection.headers["User-Agent"]
    'MyCoolTool/0.2 (xyz@example.org) mwclient/0.11.0 (https://github.com/mwclient/mwclient)'

If you want to leave mwclient's agent string out entirely, you can use
the ``custom_headers`` argument instead of ``clients_useragent``.

.. _Wikimedia User-Agent policy: https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy

.. _errors:

Using a proxy
-------------

If you need to use a proxy, you can configure the :class:`requests.Session`
using the `connection_options` parameter of the :class:`~mwclient.client.Site`.

.. code-block:: python

    import mwclient

    proxies = {
      'http': 'http://10.10.1.10:3128',
      'https': 'http://10.10.1.10:1080',
    }
    site = mwclient.Site('en.wikipedia.org', connection_options={"proxy": proxies})

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

OAuth 1 Authentication
^^^^^^^^^^^^^^^^^^^^^^

Currently, mwclient does not support OAuth 2, only OAuth 1. When reading the
upstream documentation, please refer to the OAuth 1 section.

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

.. _clientlogin:

Clientlogin authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^

The :meth:`~mwclient.client.Site.clientlogin` method supports authentication
using the ``clientlogin`` API, currently recommended by upstream for non-oauth
authentication.

For simple username-password authentication, you can do:

    >>> site.clientlogin(username='myusername', password='secret')

However, ``clientlogin`` can be called with arbitrary kwargs which are passed
through, potentially enabling many different authentication processes,
depending on server configuration.

``clientlogin`` will retrieve and add the ``logintoken`` kwarg automatically,
and add a ``loginreturnurl`` kwarg if neither it nor ``logincontinue`` is set.

It returns ``True`` if login immediately succeeds, and raises an error if it
fails. Otherwise it returns the response from the server for your application
to parse. You will need to do something appropriate with the response and then
call ``clientlogin`` again with updated arguments. Please see the
`upstream documentation`_ for more details.

.. _upstream documentation: https://www.mediawiki.org/wiki/API:Login#Method_2._action=clientlogin

.. _username-password:

Legacy Username-Password Authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. warning::
    Username-Password authentication is not recommended for Wikimedia wikis.
    See :ref:`oauth` for the recommended authentication method.

To use the legacy ``login`` interface, call :meth:`~mwclient.client.Site.login`
with your username and password. If login fails, a
:class:`mwclient.errors.LoginError` will be raised.

    >>> site.login('my_username', 'my_password')

For sites that use "bot passwords", you can use this method to login with a
bot password. From mediawiki 1.27 onwards, logging in this way with an
account's main password is deprecated, and may stop working at some point.
It is recommended to use :ref:`oauth`, :ref:`clientlogin`, or a bot password
instead.

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
