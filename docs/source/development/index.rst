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

mwclient ships with a test suite based on `pytest <https://pytest.org>`_. While
it's far from complete, it can sometimes alert you if you break things.

To run the test suite, you can use `tox <https://tox.testrun.org/>`_. Tox will
create a virtual environment for each Python version you want to test with,
install the dependencies, and run the tests.

.. code:: bash

    $ pip install tox
    $ tox

If you want to run the tests for a single Python version, you can do so by
specifying the Python version, e.g. to run the tests for Python 3.9:

.. code:: bash

    $ tox -e py39

Alternatively, you can run the tests directly with pytest:

.. code:: bash

    $ pip install -e '.[testing]'
    $ py.test

There is a container-based integration test suite which is not run by default
as it requires docker or podman, is a little slow, and needs to do ~3G of network
transfer when first run (to download the mediawiki container images). It is
run as part of CI. To run it locally, make sure you have docker or podman
installed, then with tox, do:

.. code:: bash

    $ tox -e integration

Or with pytest, do:

.. code:: bash

    $ py.test test/integration.py

If you would like to expand the test suite by adding more tests, please go ahead!

Updating/expanding the documentation
------------------------------------

The documentation for this project consists of two main parts:

1. A manually compiled user guide (located in ``docs/user/``).
2. A reference guide automatically generated from docstrings using Sphinx
   autodoc with the napoleon extension.

Builds
^^^^^^

Automatic Builds
""""""""""""""""

Documentation is automatically built on `ReadTheDocs <https://mwclient.readthedocs.io/>`_
after each commit. The configuration for this can be found in ``.readthedocs.yaml``.

Local Builds
""""""""""""

To build and test the documentation on your local machine:

1. Install the documentation dependencies:

    .. code:: bash

        $ pip install -e '.[docs]'

2. Build the documentation:

    .. code:: bash

        $ cd docs
        $ make html

The generated HTML documentation will be available in ``docs/build/html/``.
Open ``docs/build/html/index.html`` in your browser to view it.

If you make
changes to the documentation, you can rebuild it by running ``make html``
again and then refreshing the page in your browser. To rebuild after making
changes, run ``make html`` again and refresh your browser.

Writing Docstrings
^^^^^^^^^^^^^^^^^^

When writing docstrings, try to adhere to the
`Google style <https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html>`_.
For example:

.. code:: python

    def my_function(foo: str) -> str:
        """This is a function that does something.

        Args:
            foo: A string to do something with.

        Returns:
            A string with the result.
        """


You can also use `Sphinx-specific directives <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html>`_
in your docstrings to provide additional information. Some useful directives
include:

    - ``.. warning ::``: Highlight potential issues.
    - ``.. note ::``: Provide additional information.
    - ``.. seealso ::``: Link to related documentation.
    - ``.. deprecated ::``: Mark a function as deprecated.

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
when you push your branch. Tests will be automatically run on your pull
request via GitHub Actions.

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
