#!/usr/bin/env python
# encoding=utf-8
from __future__ import print_function
import os
import sys

try:
    from setuptools import setup
    from setuptools.command.test import test as TestCommand
except ImportError:
    print("This package requires 'setuptools' to be installed.")
    sys.exit(1)


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = '-v --pep8 tests mwclient --cov mwclient'

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # Import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()

requirements = ['requests_oauthlib', 'six']
if sys.version_info < (2, 7):
    requirements.append('ordereddict')

setup(name='mwclient',
      version='0.8.2',  # Rember to also update __ver__ in client.py
      description='MediaWiki API client',
      long_description=README,
      classifiers=[
          'Programming Language :: Python',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5'
      ],
      keywords='mediawiki wikipedia',
      author='Bryan Tong Minh',
      author_email='bryan.tongminh@gmail.com',
      url='https://github.com/btongminh/mwclient',
      license='MIT',
      packages=['mwclient'],
      cmdclass={'test': PyTest},
      tests_require=['pytest-pep8', 'pytest-cache', 'pytest', 'pytest-cov', 'responses>=0.3.0', 'mock'],
      install_requires=requirements,
      zip_safe=True
      )
