
.. figure:: docs/source/logo.png
   :alt: Logo
   :align: center

mwclient
========

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
   :target: http://mwclient.readthedocs.io/en/latest/
   :alt: Documentation status

.. image:: http://isitmaintained.com/badge/resolution/tldr-pages/tldr.svg
   :target: http://isitmaintained.com/project/tldr-pages/tldr
   :alt: Issue statistics

mwclient is a lightweight Python client library to the `MediaWiki API <https://mediawiki.org/wiki/API>`_
which provides access to most API functionality.
It works with Python 2.7, 3.3 and above, and supports MediaWiki 1.16 and above.
For functions not available in the current MediaWiki, a ``MediaWikiVersionError`` is raised.

The current stable `version 0.8.4 <https://github.com/mwclient/mwclient/archive/v0.8.4.zip>`_
was released on 23 February 2017, and is `available through PyPI <https://pypi.python.org/pypi/mwclient>`_:

.. code-block:: console

    $ pip install mwclient

The current `development version <https://github.com/mwclient/mwclient>`_
can be installed from GitHub:

.. code-block:: console

    $ pip install git+git://github.com/mwclient/mwclient.git

Please see the
`changelog document <https://github.com/mwclient/mwclient/blob/master/CHANGELOG.md>`_
for a list of changes.

Getting started
---------------

See the `user guide <http://mwclient.readthedocs.io/en/latest/user/index.html>`_
to get started using mwclient.

For more information, see the
`REFERENCE.md <https://github.com/mwclient/mwclient/blob/master/REFERENCE.md>`_ file
and the `documentation on the wiki <https://github.com/mwclient/mwclient/wiki>`_.


Contributing
--------------------

mwclient ships with a test suite based on `pytest <https://pytest.org>`_.
Only a small part of mwclient is currently tested,
but hopefully coverage will improve in the future.

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

*Documentation* consists of both a manually compiled user guide (under ``docs/user``)
and a reference guide generated from the docstrings,
using Sphinx autodoc with the napoleon extension.
Documentation is built automatically on `ReadTheDocs`_ after each commit.
To build documentation locally for testing, do:

.. code-block:: console

  $ cd docs
  $ make html

When writing docstrings, try to adhere to the `Google style`_.

.. _Google style: https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html
.. _ReadTheDocs: https://mwclient.readthedocs.io/

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
