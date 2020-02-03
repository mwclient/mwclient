.. _implementation-notes:

Implementation notes
====================

Most properties and generators accept the same parameters as the API, without their two-letter prefix.
Some notable exceptions:

* ``Image.imageinfo`` is the imageinfo of the latest image. Earlier versions can be fetched using ``imagehistory()``.
* ``Site.all*``: parameter ``(ap)from`` renamed to ``start``
* ``categorymembers`` is implemented as ``Category.members``
* ``deletedrevs`` is ``deletedrevisions``
* ``usercontribs`` is ``usercontributions``
* First parameters of ``search`` and ``usercontributions`` are ``search`` and ``user``, respectively

Properties and generators are implemented as Python generators. Their limit parameter is only an indication of the number of items in one chunk. It is not the total limit. Doing ``list(generator(limit = limit))`` will return ALL items of generator, and not be limited by the limit value. Use ``list(generator(max_items = max_items))`` to limit the amount of items returned. Default chunk size is generally the maximum chunk size.

Page objects
------------

The base Page object is called ``Page``
and from that derive ``Category`` and ``Image``.
When the page is retrieved via ``Site.pages`` or a generator,
it will check automatically which of those three specific types
should be returned.

For convenience, ``Site.images`` and ``Site.categories`` are also provided.
These do exactly the same as `Site.Pages`, except that they require the page name
without its namespace prefixed.

    >>> page = site.Pages['Template:Stub']   # a Page object
    >>> image = site.Pages['Image:Wiki.png'] # an Image object
    >>> image = site.Images['Wiki.png']      # the same Image object
    >>> cat = site.Pages['Category:Python']  # a Category object
    >>> cat = site.Images['Python']          # the same Category object
