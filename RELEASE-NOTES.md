# Release Notes for mwclient

## Changes in version 0.7
* [2013-11-15] Ask a query against Semantic MediaWiki.
  (by [@kyv](https://github.com/kyv))
  [0a16afc](https://github.com/kyv/mwclient/commit/0a16afc)
* [2012-08-30] Allow setting both the upload description and the page content separately
  (by [@btongminh](https://github.com/btongminh))
  [0aa748f](https://github.com/btongminh/mwclient/commit/0aa748f) 
* [2012-08-30] Improve documentation
  (by [@tommorris](https://github.com/tommorris))
  [a2723e7](https://github.com/btongminh/mwclient/commit/a2723e7)
* [2013-02-15] Converted the repository to git and moved from sourceforge to github
  (by [@waldir](https://github.com/waldir))
  [#1](https://github.com/btongminh/mwclient/issues/1) (also
  [#11](https://github.com/btongminh/mwclient/issues/11),
  [#13](https://github.com/btongminh/mwclient/issues/13) and
  [#15](https://github.com/btongminh/mwclient/issues/15))
* [2013-03-20] Support for customising the useragent
  (by [@eug48](https://github.com/eug48))
  [773adf9](https://github.com/btongminh/mwclient/commit/773adf9),
  [#16](https://github.com/btongminh/mwclient/pull/16)
* [2013-03-20] Removed unused 'Request' class 
  (by [@eug48](https://github.com/eug48))
  [99e786d](https://github.com/btongminh/mwclient/commit/99e786d),
  [#16](https://github.com/btongminh/mwclient/pull/16)
* [2013-05-13] Support for requesting pages by their page id (`site.pages[page_id]`)
  (by [@danmichaelo](https://github.com/danmichaelo))
  [a1a2ced](https://github.com/danmichaelo/mwclient/commit/a1a2ced),
  [#19](https://github.com/btongminh/mwclient/pull/19)
* [2013-05-13] Support for editing sections
  (by [@danmichaelo](https://github.com/danmichaelo))
  [546f77d](https://github.com/danmichaelo/mwclient/commit/546f77d),
  [#19](https://github.com/btongminh/mwclient/pull/19)
* [2013-05-13] New method `Page.redirects_to()` and helper method `Page.resolve_redirect()`
  (by [@danmichaelo](https://github.com/danmichaelo))
  [3b851cb](https://github.com/danmichaelo/mwclient/commit/3b851cb),
  [36e8dcc](https://github.com/danmichaelo/mwclient/commit/36e8dcc),
  [#19](https://github.com/btongminh/mwclient/pull/19)
* [2013-05-13] Support argument `action` with `logevents()`
  (by [@danmichaelo](https://github.com/danmichaelo))
  [241ed37](https://github.com/danmichaelo/mwclient/commit/241ed37),
  [#19](https://github.com/btongminh/mwclient/pull/19)
* [2013-05-13] Support argument `page` with `parse()`
  (by [@danmichaelo](https://github.com/danmichaelo))
  [223aa0](https://github.com/danmichaelo/mwclient/commit/223aa0),
  [#19](https://github.com/btongminh/mwclient/pull/19)

## Changes in version 0.6.5
Mwclient 0.6.5 was released on 6 May 2011
* Explicitly convert the `Content-Length` header to `str`,
  avoiding a `TypeError` on some versions of Python.
* Fix for upload by URL
* Handle `readapidenied` error in site init
* Fix version parsing for almost any sane version string

## Changes in version 0.6.4
Mwclient 0.6.3 was released on 7 April 2010
* Added support for upload API
* Added `prop=duplicatefiles`
* Properly fix detection of alpha versions
* Added support for built-in JSON library
* Handle badtoken once
* [Bug 2690034](https://github.com/mwclient/mwclient/issues/3):
  Fix revision iteration
* Fix module conflict with simplejson-1.x
  by inserting mwclient path at the beginning of `sys.path`
  instead of the end
* Supply token on login if necessary

## Changes in version 0.6.3
Mwclient 0.6.3 was released on 16 July 2009
* Added domain parameter to login.
* Applied edit fix to `page_nowriteapi`
* Allow arbitrary data to be passed to `page.save`
* Fix mwclient on WMF wikis

## Changes in version 0.6.2
Mwclient 0.6.2 was released on 2 May 2009.
* Compatibility fixes for MediaWiki 1.13
* Download fix for images
* Full support for editing pages via write API
  and split of compatibility to another file.
* Added `expandtemplates` API call
* Added and fixed moving via API
* Raise an `ApiDisabledError` if the API is disabled
* Added support for HTTPS
* Fixed email code
* Mark edits as bots by default.
* Added `action=parse`. Modified patch by Brian Mingus.
* Improved general HTTP and upload handling.

## Changes in version 0.6.1
Mwclient 0.6.1 was released in May 2008.
No release notes were kept for this version.

## Changes in version 0.6.0
Mwclient 0.6.0 was released in February 2008.
This was the first official release via Sourceforge.
This version removed some Pywikipedia influences added in 0.4.

## Changes in versions 0.5
Mwclient 0.5 was an architectural redesign
which accomplished easy extendability
and added proper support for continuations. 

## Changes in version 0.4
Mwclient 0.4 was somewhat the basis for future releases
and shows the current module architecture.
It was influenced by Pywikipedia,
which was discovered by the author at the time.

## Changes in versions 0.2 and 0.3
Mwclient 0.2 and 0.3 were probably a bit of a generalization,
and maybe already used the API for some part,
but details are unknown.

## Mwclient 0.1
Mwclient 0.1 was a non-API module for accessing Wikipedia using an XML parser.
