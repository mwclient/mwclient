mwclient
========

Mwclient is a client to the `MediaWiki API <//mediawiki.org/wiki/API>`_
which provides access to most API functionality.
It depends heavily on Bob Ippolito's `SimpleJSON <//github.com/simplejson/simplejson>`_,
requires Python 2.4 and supports MediaWiki 1.11 and above.
For functions not available in the current MediaWiki, a ``MediaWikiVersionError`` is raised.

This framework was written by Bryan Tong Minh, who released the latest stable 
`version 0.6.5 <//github.com/mwclient/mwclient/archive/REL_0_6_5.zip>`_ on 6 May 2011.
The current `development version <//github.com/mwclient/mwclient>`_
can be installed directly off github:

.. code-block:: console

    $ pip install git+git://github.com/mwclient/mwclient.git

Please see the `release notes <//github.com/mwclient/mwclient/blob/master/RELEASE-NOTES.md>`_
for a list of changes.

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


HTTPS
-----

To use https, specify the host as a tuple in the form of ``('https', hostname)``.


Example
-------

For more information, see the
`REFERENCE.md <//github.com/mwclient/mwclient/blob/master/REFERENCE.md>`_ file.

.. code-block:: python

	# Initialize Site object
	import mwclient
	site = mwclient.Site('commons.wikimedia.org')
	site.login(username, password)  # Optional

	# Edit page
	page = site.Pages['Commons:Sandbox']
	text = page.edit()
	print 'Text in sandbox:', text.encode('utf-8')
	page.save(text + u'\nExtra data', summary = 'Test edit')

	# Printing imageusage
	image = site.Images['Example.jpg']
	print 'Image', image.name.encode('utf-8'), 'usage:'
	for page in image.imageusage():
		print 'Used:', page.name.encode('utf-8'), '; namespace', page.namespace
		print 'Image info:', image.imageinfo

	# Uploading a file
	site.upload(open('file.jpg'), 'destination.jpg', 'Image description')

	# Listing all categories (don't do this in reality)
	for category in site.allcategories():
		print category
