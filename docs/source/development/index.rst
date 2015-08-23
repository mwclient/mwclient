.. _development:

Development
===========

Mwclient development is coordinated at https://github.com/mwclient/mwclient.
Patches are very welcome. There's currently no chat room or mailing list
for the project, but don't hesitate to use the issue tracker at GitHub for
general discussions.

Development environment
-----------------------

If you plan to submit a pull request, you should first
`fork <https://github.com/mwclient/mwclient#fork-destination-box>`_
the mwclient repo on GitHub, then clone your own fork:

.. code:: bash

    $ git clone git@github.com:MYUSERNAME/mwclient.git
    $ cd mwclient

You can then use pip to do an "editable" install so that your
edits will be immediately available for (both interactive
and automated) testing:

.. code:: bash

    $ pip install -e .

Running tests
-------------

To run the automated tests, install the test dependencies and run `pytest <http://pytest.org/>`_:

.. code:: bash

    $ pip install pytest pytest-pep8 responses
    $ py.test

To run tests with different Python versions in isolated virtualenvs, you can use `Tox <https://tox.testrun.org/>`_:

.. code:: bash

    $ pip install tox
    $ tox


Note that the test suite is quite limited yet.
If you'd like to expand it by adding more tests, please go ahead!

Making a pull request
---------------------

Make sure to run tests before committing. When it comes to the commit message,
there's no specific requirements for the format, but try to explain your changes
in a clear and concise manner.

If it's been some time since you forked, please consider rebasing your branch
on the main master branch to ease merging:

.. code:: bash

    $ git remote add upstream https://github.com/mwclient/mwclient.git
    $ git rebase upstream master

Then push your code and open a pull request on GitHub.
