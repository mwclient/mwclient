#!/usr/bin/env python
# encoding=utf-8
from __future__ import print_function
import os
import sys
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()

setup(name='mwclient',
      version='0.8.6',  # Use bumpversion to update
      description='MediaWiki API client',
      long_description=README,
      classifiers=[
          'Programming Language :: Python',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
      ],
      keywords='mediawiki wikipedia',
      author='Bryan Tong Minh',
      author_email='bryan.tongminh@gmail.com',
      url='https://github.com/btongminh/mwclient',
      license='MIT',
      packages=['mwclient'],
      install_requires=['requests_oauthlib', 'six'],
      setup_requires=['pytest-runner'],
      tests_require=['pytest', 'pytest-pep8', 'pytest-cache', 'pytest-cov',
                     'responses>=0.6.0', 'mock'],
      zip_safe=True
      )
