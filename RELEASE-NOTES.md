# RELEASE NOTES FOR MWCLIENT #

This is mwclient 0.6.6. The following are the release notes for this version.

## Changes in version 0.6.6 ##
* Allow setting both the upload description and the page content separately

## Changes in version 0.6.5 ##
* Explicitly convert the `Content-Length` header to `str`,
  avoiding a `TypeError` on some versions of Python.
* Fix for upload by URL
* Handle `readapidenied` error in site init
* Fix version parsing for almost any sane version string

## Changes in version 0.6.4 ##
* Added support for upload API
* Added `prop=duplicatefiles`
* Properly fix detection of alpha versions
* Added support for built-in JSON library
* Handle badtoken once
* Bug 2690034: Fix revision iteration
* Fix module conflict with simplejson-1.x
  by inserting mwclient path at the beginning of `sys.path`
  instead of the end
* Supply token on login if necessary

## Changes in version 0.6.3 ##
* Added domain parameter to login.
* Applied edit fix to `page_nowriteapi`
* Allow arbitrary data to be passed to `page.save`
* Fix mwclient on WMF wikis

## Changes in version 0.6.2 ##
Mwclient was released on 2 May 2009.
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

## Changes in version 0.6.1 and 0.6.0 ##
Mwclient 0.6.1 was released in May 2008.
No release notes were kept for that version.

Mwclient 0.6.0 was released in February 2008.
It was the first official release via Sourceforge.
This version removed some Pywikipedia influences added in 0.4.

## Mwclient 0.5 ##
Mwclient 0.5 was an architectural redesign
which accomplished easy extendability
and added proper support for continuations. 

## Mwclient 0.4 ##
Mwclient 0.4 was somewhat the basis for future releases
and shows the current module architecture.
It was influenced by Pywikipedia,
which was discovered by the author at the time.

## Mwclient 0.2 and 0.3 ##
Mwclient 0.2 and 0.3 were probably a bit of a generalization,
and maybe already used the API for some part,
but details are unknown.

## Mwclient 0.1 ##
Mwclient 0.1 was a non-API module for accessing Wikipedia using an XML parser.
