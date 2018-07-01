<div align="center"><img src="docs/source/logo.svg" width="300"/></div>

# mwclient

[![Build status][build-status-img]](https://travis-ci.org/mwclient/mwclient)


[![Test coverage][test-coverage-img]](https://coveralls.io/r/mwclient/mwclient)
[![Code health][code-health-img]](https://landscape.io/github/mwclient/mwclient/master)
[![Latest version][latest-version-img]](https://pypi.python.org/pypi/mwclient)
[![MIT license][mit-license-img]](http://opensource.org/licenses/MIT)
[![Documentation status][documentation-status-img]](http://mwclient.readthedocs.io/en/latest/)
[![Issue statistics][issue-statistics-img]](http://isitmaintained.com/project/tldr-pages/tldr)
[![Gitter chat][gitter-chat-img]](https://gitter.im/mwclient/mwclient)


[build-status-img]: https://img.shields.io/travis/mwclient/mwclient.svg
[test-coverage-img]: https://img.shields.io/coveralls/mwclient/mwclient.svg
[code-health-img]: https://landscape.io/github/mwclient/mwclient/master/landscape.svg?style=flat
[latest-version-img]: https://img.shields.io/pypi/v/mwclient.svg
[mit-license-img]: https://img.shields.io/github/license/mwclient/mwclient.svg
[documentation-status-img]: https://readthedocs.org/projects/mwclient/badge/?version=master
[issue-statistics-img]: http://isitmaintained.com/badge/resolution/tldr-pages/tldr.svg
[gitter-chat-img]: https://img.shields.io/gitter/room/mwclient/mwclient.svg

mwclient is a lightweight Python client library to the
[MediaWiki API](https://mediawiki.org/wiki/API)
which provides access to most API functionality.
It works with Python 2.7, 3.3 and above,
and supports MediaWiki 1.16 and above.
For functions not available in the current MediaWiki,
a `MediaWikiVersionError` is raised.

The current stable
[version 0.8.7](https://github.com/mwclient/mwclient/archive/v0.8.7.zip)
is [available through PyPI](https://pypi.python.org/pypi/mwclient):

```
$ pip install mwclient
```

The current [development version](https://github.com/mwclient/mwclient)
can be installed from GitHub:

```
$ pip install git+git://github.com/mwclient/mwclient.git
```

Please see the [changelog
document](https://github.com/mwclient/mwclient/blob/master/CHANGELOG.md)
for a list of changes.

## Getting started

See the
[user guide](http://mwclient.readthedocs.io/en/latest/user/index.html)
to get started using mwclient.

For more information, see the
[REFERENCE.md](https://github.com/mwclient/mwclient/blob/master/REFERENCE.md) file
and the [documentation on the wiki](https://github.com/mwclient/mwclient/wiki).

## Contributing

mwclient ships with a test suite based on [pytest](https://pytest.org).
Only a small part of mwclient is currently tested,
but hopefully coverage will improve in the future.

The easiest way to run the tests is:

```
$ python setup.py test
```

This will make an in-place build
and download test dependencies locally if needed.
To make tests run faster, you can use pip to do an
["editable" install](https://pip.readthedocs.org/en/latest/reference/pip_install.html#editable-installs):

```
$ pip install pytest pytest-pep8 responses
$ pip install -e .
$ py.test
```

To run tests with different Python versions in isolated virtualenvs,
you can use [Tox](https://testrun.org/tox/latest/):

```
$ pip install tox
$ tox
```

*Documentation* consists of both a manually compiled user guide
(under `docs/user`) and a reference guide generated from the docstrings,
using Sphinx autodoc with the napoleon extension.
Documentation is built automatically on [ReadTheDocs](https://mwclient.readthedocs.io/)
after each commit.
To build the documentation locally for testing, do:

```
$ cd docs
$ make html
```

When writing docstrings, try to adhere to the
[Google style](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html).

# Implementation notes

Most properties and generators accept the same parameters as the API,
without their two-letter prefix. Exceptions to this rule:

- `Image.imageinfo` is the imageinfo of the latest image.
   Earlier versions can be fetched using `imagehistory()`
- `Site.all*`: parameter `[ap]from` renamed to `start`
- `categorymembers` is implemented as `Category.members`
- `deletedrevs` is `deletedrevisions`
- `usercontribs` is `usercontributions`
- First parameters of `search` and `usercontributions`
  are `search` and `user` respectively

Properties and generators are implemented as Python generators.
Their limit parameter is only an indication
of the number of items in one chunk.
It is not the total limit.
Doing `list(generator(limit = limit))` will return ALL items of generator,
and not be limited by the limit value.
Default chunk size is generally the maximum chunk size.
