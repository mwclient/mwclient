This file is intended to be a reference to mwclient.
The current version is mwclient 0.6.5.

The mwclient framework provides access to the MediaWiki API.
It provides the functions of the MediaWiki API in a Pythonic manner.

## Sites ##
The `Site` object is the most important class.
It represents a MediaWiki site.
Its constructor accepts various arguments,
of which the first two, `host` and `path`, are the most important.
They represent respectively
the hostname without protocol
and the root directory where `api.php` is located.
The path parameter should end with a slash, /.
Protocols other than HTTP and HTTPS are currently not supported.

```python
#http
site = mwclient.Site(host, path = '/w/', ...)

#https
site = mwclient.Site(('https', host), path = '/w/', ...)
```

### Pages ###
Sites provide access to pages via various generators and the Pages object.
The base Page object is called Page
and from that derive Category and Image.
When the page is retrieved via `Site.Pages` or a generator,
it will check automatically which of those three specific types
should be returned.
To get a page by its name, call `Site.Pages` as a scriptable object:

```python
page = site.Pages['Template:Stub']
image = site.Pages['Image:Wiki.png'] # This will return an Image object
image2 = site.Images['Wiki.png'] # The same image
```

Alternatively, `Site.Images` and `Site.Categories` are provided,
which do exactly the same as `Site.Pages`,
except that they require the page name without its namespace prefixed.

#### PageProperties ####
The `Page` object provides many generators available in the API.
In addition to the page properties listed in the API documentation,
also the lists backlinks and embedded in are members of the Page object. For more information about using generators
see the section on generators below.

`Category` objects provide an extra function, `members`
to list all members of a category.
The Category object can also be used itself
as an iterator yielding all its members.

```python
#list pages in Category:Help by name
category = site.Pages['Category:Help']
for page in category:
	print page.name
```

`Image` objects have additional functions `imagehistory` and `imageusage`
which represent the old versions of the image and its usage, respectively.
`Image.download` returns a file object to the full size image.

```python
fr = image.download()
fw = open('Wiki.png', 'rb')
while True:
	s = fr.read(4096)
	if not s: break
	fw.write(s)
fr.close() # Always close those file objects !!!
fw.close()
```

#### Editing pages ####
Call `Page.text()` to retrieve the page content.
Use `Page.save(text, summary = u'', ...)` to save the page.
If available, `Page.save` uses the API to edit,
but falls back to the old way if the write API is not available.

## Generators ##

## Exceptions ##

## Implementation notes ##
Most properties and generators accept the same parameters as the API,
without their two-letter prefix.
Exceptions:
* `Image.imageinfo` is the `imageinfo` of the *latest* image.
Earlier versions can be fetched using `imagehistory()`
* `Site.all*`: parameter `(ap)from` renamed to `start`
* `categorymembers` is implemented as `Category.members`
* `deletedrevs` is `deletedrevisions`
* `usercontribs` is `usercontributions`
* First parameters of `search` and `usercontributions`
  are `search` and `user`, respectively

Properties and generators are implemented as Python generators.
Their limit parameter is only an indication
of the number of items in one chunk.
It is not the total limit.
Doing `list(generator(limit = limit))` will return
ALL items of generator, and not be limited by the limit value.
Use `list(generator(max_items = max_items))`
to limit the amount of items returned.
Default chunk size is generally the maximum chunk size.

## Links ##
* Project page at GitHub: https://github.com/mwclient/mwclient
* More in-depth documentation on the GitHub wiki: 
https://github.com/mwclient/mwclient/wiki
* MediaWiki API documentation: https://mediawiki.org/wiki/API
