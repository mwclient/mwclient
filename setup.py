#!/usr/bin/env python
import os
import sys
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()

needs_pytest = set(['pytest', 'test', 'ptr']).intersection(sys.argv)
pytest_runner = ['pytest-runner'] if needs_pytest else []

setup(name='mwclient',
      version='0.10.1',  # Use bumpversion to update
      description='MediaWiki API client',
      long_description=README,
      long_description_content_type='text/markdown',
      classifiers=[
          'Programming Language :: Python',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.10',
          'Programming Language :: Python :: 3.11',
          'Programming Language :: Python :: 3.12',
      ],
      keywords='mediawiki wikipedia',
      author='Bryan Tong Minh',
      author_email='bryan.tongminh@gmail.com',
      url='https://github.com/mwclient/mwclient',
      license='MIT',
      packages=['mwclient'],
      install_requires=['requests-oauthlib'],
      setup_requires=pytest_runner,
      tests_require=['pytest', 'pytest-cov',
                     'responses>=0.3.0', 'responses!=0.6.0', 'setuptools'],
      zip_safe=True
      )
