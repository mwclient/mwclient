
.. image:: https://img.shields.io/travis/mwclient/mwclient.svg
   :target: https://travis-ci.org/mwclient/mwclient
   :alt: Build status

.. image:: https://img.shields.io/coveralls/mwclient/mwclient.svg
   :target: https://coveralls.io/r/mwclient/mwclient
   :alt: Test coverage

.. image:: https://landscape.io/github/mwclient/mwclient/master/landscape.svg?style=flat
   :target: https://landscape.io/github/mwclient/mwclient/master
   :alt: Code health

.. image:: https://img.shields.io/pypi/v/mwclient.svg
   :target: https://pypi.python.org/pypi/mwclient
   :alt: Latest version

.. image:: https://img.shields.io/pypi/dw/mwclient.svg
   :target: https://pypi.python.org/pypi/mwclient
   :alt: Downloads

.. image:: https://img.shields.io/github/license/mwclient/mwclient.svg
   :target: http://opensource.org/licenses/MIT
   :alt: MIT license

.. image:: https://readthedocs.org/projects/mwclient/badge/?version=master
   :target: https://readthedocs.org/projects/mwclient/?badge=master
   :alt: Documentation Status

mwclient
========

mwclient is a lightweight Python client library to the `MediaWiki API <https://mediawiki.org/wiki/API>`_
which provides access to most API functionality.
It works with Python 2.6, 2.7, 3.3 and above, and supports MediaWiki 1.16 and above.
For functions not available in the current MediaWiki, a ``MediaWikiVersionError`` is raised.

This framework was written by Bryan Tong Minh, who maintained the project until
version 0.6.5, released on 6 May 2011. The current stable
`version 0.8.1 <https://github.com/mwclient/mwclient/archive/v0.8.1.zip>`_
was released on 5 February 2016, and is `available through PyPI <https://pypi.python.org/pypi/mwclient>`_:

.. code-block:: console

    $ pip install mwclient

The current `development version <https://github.com/mwclient/mwclient>`_
can be installed from GitHub:

.. code-block:: console

    $ pip install git+git://github.com/mwclient/mwclient.git

Please see the 
`release notes <https://github.com/mwclient/mwclient/blob/master/RELEASE-NOTES.md>`_
for a list of changes.

Contributing
--------------------

mwclient ships with a test suite based on `pytest <https://pytest.org>`_.
Only a small part of mwclient is currently tested, but hopefully coverage
will improve in the future.

The easiest way to run tests is:

.. code-block:: console

    $ python setup.py test

This will make an in-place build and download test dependencies locally
if needed. To make tests run faster, you can use pip to do an
`"editable" install <https://pip.readthedocs.org/en/latest/reference/pip_install.html#editable-installs>`_:

.. code-block:: console

    $ pip install pytest pytest-pep8 responses
    $ pip install -e .
    $ py.test

To run tests with different Python versions in isolated virtualenvs, you
can use `Tox <https://testrun.org/tox/latest/>`_:

.. code-block:: console

    $ pip install tox
    $ tox

Implementation notes
--------------------

Most properties and generators accept the same parameters as the API,
without their two-letter prefix. Exceptions to this rule:

* ``Image.imageinfo`` is the imageinfo of the latest image.
  Earlier versions can be fetched using ``imagehistory()``
* ``Site.all*``: parameter ``[ap]from`` renamed to ``start``
* ``categorymembers`` is implemented as ``Category.members``
* ``deletedrevs`` is ``deletedrevisions``
* ``usercontribs`` is ``usercontributions``
* First parameters of ``search`` and ``usercontributions`` are ``search`` and ``user`` 
  respectively

Properties and generators are implemented as Python generators.
Their limit parameter is only an indication of the number of items in one chunk.
It is not the total limit.
Doing ``list(generator(limit = limit))`` will return ALL items of generator,
and not be limited by the limit value.
Default chunk size is generally the maximum chunk size.


HTTPS
-----

mwclient uses https as default from version 0.8.0. To use http instead,
specify the host as a tuple in the form of ``('http', hostname)``.


User-agents
-----------
Bots that run on Wikimedia wikis `require an informative user-agent for all
API requests <https://meta.wikimedia.org/wiki/User-Agent_policy>`_. To change
the user-agent, you will need to include an appropriate parameter for 
``clients_useragent`` when you initialize your ``Site``, as shown in the
following example:

.. code-block:: python

    useragent = 'YourBot, based on mwclient v0.7.2. Run by User:You, you@gmail.com'
    site = mwclient.Site('en.wikipedia.org', clients_useragent=useragent)


Example
-------

For more information, see the
`REFERENCE.md <https://github.com/mwclient/mwclient/blob/master/REFERENCE.md>`_ file
or the 
`documentation on the wiki <https://github.com/mwclient/mwclient/wiki>`_.

.. code-block:: python

	# Initialize Site object
	import mwclient
	site = mwclient.Site('commons.wikimedia.org')
	site.login(username, password)

	# Edit page
	page = site.Pages['Commons:Sandbox']
	text = page.text()
	print 'Text in sandbox:', text.encode('utf-8')
	page.save(text + u'\nExtra data', summary = 'Test edit')

	# Printing imageusage
	image = site.Images['Example.jpg']
	print 'Image', image.name.encode('utf-8'), 'usage:'
	for page in image.imageusage():
		print 'Used:', page.name.encode('utf-8'), '; namespace', page.namespace
		print 'Image info:', image.imageinfo

	# Uploading a file
	site.upload(open('file.jpg'), 'destination.jpg', 'Image description')

	# Listing all categories (don't do this in reality)
	for category in site.allcategories():
		print category
