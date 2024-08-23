#!/usr/bin/env python
import os

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md'), "r", encoding="utf-8") as f:
    README = f.read()

setup(name='mwclient',
      # See https://mwclient.readthedocs.io/en/latest/development/#making-a-release
      # for how to update this field and release a new version.
      version='0.11.0',
      description='MediaWiki API client',
      long_description=README,
      long_description_content_type='text/markdown',
      classifiers=[
          'Programming Language :: Python',
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
      extras_require={
          'testing': ['pytest', 'pytest-cov',
                      'responses>=0.3.0', 'responses!=0.6.0', 'setuptools'],
      },
      zip_safe=True
      )
