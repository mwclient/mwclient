.. _development:

Development
===========

Mwclient development is coordinated at https://github.com/mwclient/mwclient.
Patches are very welcome. If there's something you want to discuss first,
we have a `Gitter chatroom <https://gitter.im/mwclient/mwclient>`_.

Development environment
-----------------------

If you plan to submit a pull request, you should first
`fork <https://github.com/mwclient/mwclient#fork-destination-box>`_
the mwclient repo on GitHub, then check out the original repository
and configure your fork as a remote:

.. code:: bash

    $ git clone https://github.com/mwclient/mwclient.git
    $ cd mwclient
    $ git remote add fork git@github.com:MYUSERNAME/mwclient.git

You can then use pip to do an "editable" install so that your
edits will be immediately available for (both interactive
and automated) testing:

.. code:: bash

    $ pip install -e .

Create a new branch for your changes:

.. code:: bash

    $ git checkout -b my-branch

Test suite
----------

mwclient ships with a test suite based on `pytest <https://pytest.org>`_.
While it's far from complete, it can sometimes alert you if you break things.

The easiest way to run the tests is:

.. code:: bash

    $ python setup.py test

This will make an in-place build and download test dependencies locally if needed.
Tests will run faster, however, if you do an
`editable install <https://pip.readthedocs.org/en/latest/reference/pip_install.html#editable-installs>`_
and run pytest directly:

.. code:: bash

    $ pip install pytest pytest-cov flake8 responses mock
    $ pip install -e .
    $ py.test

If you want to test with different Python versions in isolated virtualenvs,
you can use `Tox <https://tox.testrun.org/>`_. A `tox.ini` file is included.

.. code:: bash

    $ pip install tox
    $ tox

If you would like to expand the test suite by adding more tests, please go ahead!

Updating/expanding the documentation
------------------------------------

Documentation consists of both a manually compiled user guide
(under ``docs/user``) and a reference guide generated from the docstrings,
using Sphinx autodoc with the napoleon extension.
Documentation is built automatically on `ReadTheDocs <https://mwclient.readthedocs.io/>`_
after each commit.
To build the documentation locally for testing:

.. code:: bash

    $ pip install Sphinx sphinx-rtd-theme
    $ cd docs
    $ make html

When writing docstrings, try to adhere to the
`Google style <https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html>`_.

Making a pull request
---------------------

Make sure to run tests before committing. When it comes to the commit message,
there's no specific requirements for the format, but try to explain your changes
in a clear and concise manner.

If it's been some time since you forked, please consider rebasing your branch
on the main master branch to ease merging:

.. code:: bash

    $ git rebase master

When it is ready, push your branch to your remote:

.. code:: bash

    $ git push -u fork my-branch

Then you can open a pull request on GitHub. You should see a URL to do this
when you push your branch.

Making a release
----------------

These instructions are for maintainers of the project.
To cut a release, ensure ``CHANGELOG.md`` is updated, then use
`bump-my-version <https://callowayproject.github.io/bump-my-version/>`_:

.. code:: bash

    $ pip install bump-my-version
    $ bump-my-version bump major|minor|patch

Then check the commit looks correct and is tagged vX.Y.Z, and push. The
``.github/workflows/release.yml`` action will publish to PyPI.
