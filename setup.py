#!/usr/bin/env python
# encoding=utf-8

# Bootstrap setuptools
from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup
import os

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()

setup(name='mwclient',
      version='0.7dev',
      description='MediaWiki API client',
      long_description=README,
      classifiers=[
          'Programming Language :: Python',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7'
      ],
      keywords='mediawiki wikipedia',
      author='Bryan Tong Minh',
      author_email='bryan.tongminh@gmail.com',
      url='https://github.com/btongminh/mwclient',
      license='MIT',
      packages=['mwclient'],
      install_requires=['simplejson', 'requests']
      )
