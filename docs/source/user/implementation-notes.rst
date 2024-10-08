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

Properties and generators are implemented as Python generators which yield one item per iteration. Their deprecated ``limit`` parameter is only an indication of the number of items retrieved from the API per request. It is not the total limit. Doing ``list(generator(limit = 50))`` will return ALL items, not 50, but it will query the API in chunks of 50 items at a time (so after yielding one item from the generator, the next 49 will be "free", then the next will trigger a new API call). The replacement ``api_chunk_size`` parameter does the same thing, but is more clearly named. If both ``limit`` and ``api_chunk_size`` are specified, ``limit`` will be ignored. The ``max_items`` parameter sets a total limit on the number of items which will be yielded. Use ``list(generator(max_items = 50))`` to limit the amount of items returned to 50. Higher level functions that have a ``limit`` parameter also now have ``api_chunk_size`` and ``max_items`` parameters that should be preferred. Default API chunk size is generally the maximum chunk size (500 for most wikis).

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
