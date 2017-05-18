# Release Notes for mwclient

See [GitHub releases](https://github.com/mwclient/mwclient/releases/) for
release notes for mwclient 0.7.1+.

## Changes in version 0.7.0

Mwclient 0.7.0 was released on 27 September 2014.

Upgrade notices:
 - This version requires minimum Python 2.6 and MediaWiki 1.16.
   Support for Python 2.4–2.5 and MediaWiki 1.11–1.15 has been dropped.
 - The `Page.edit()` method has been renamed to `Page.text()`.
   While `Page.edit()` is deprecated, it will be available for a long time.
   The old `Page.text` attribute, that used to store a copy of the wikitext
   from the last `Page.edit()` call, has been removed entirely.
   The `readonly` argument has also been removed (it was never really
   implemented, so it acted only as a dummy argument before the removal).
 - The `Page.get_expanded()` method has been deprecated in favour of
   calling `Page.text(expandtemplates=True)`.

Detailed changelog:
* [2012-08-30] [@btongminh](https://github.com/btongminh):
  Allow setting both the upload description and the page content separately.
  [0aa748f](https://github.com/mwclient/mwclient/commit/0aa748f).
* [2012-08-30] [@tommorris](https://github.com/tommorris):
  Improve documentation.
  [a2723e7](https://github.com/mwclient/mwclient/commit/a2723e7).
* [2013-02-15] [@waldyrious](https://github.com/waldyrious):
  Converted the repository to git and moved from sourceforge to github.
  [#1](https://github.com/mwclient/mwclient/issues/1) (also
  [#11](https://github.com/mwclient/mwclient/issues/11),
  [#13](https://github.com/mwclient/mwclient/issues/13) and
  [#15](https://github.com/mwclient/mwclient/issues/15)).
* [2013-03-20] [@eug48](https://github.com/eug48):
  Support for customising the useragent.
  [773adf9](https://github.com/mwclient/mwclient/commit/773adf9),
  [#16](https://github.com/mwclient/mwclient/pull/16).
* [2013-03-20] [@eug48](https://github.com/eug48):
  Removed unused `Request` class.
  [99e786d](https://github.com/mwclient/mwclient/commit/99e786d),
  [#16](https://github.com/mwclient/mwclient/pull/16).
* [2013-05-13] [@danmichaelo](https://github.com/danmichaelo):
  Support for requesting pages by their page id (`site.pages[page_id]`).
  [a1a2ced](https://github.com/danmichaelo/mwclient/commit/a1a2ced),
  [#19](https://github.com/mwclient/mwclient/pull/19).
* [2013-05-13] [@danmichaelo](https://github.com/danmichaelo):
  Support for editing sections.
  [546f77d](https://github.com/danmichaelo/mwclient/commit/546f77d),
  [#19](https://github.com/mwclient/mwclient/pull/19).
* [2013-05-13] [@danmichaelo](https://github.com/danmichaelo):
  New method `Page.redirects_to()` and helper method `Page.resolve_redirect()`.
  [3b851cb](https://github.com/danmichaelo/mwclient/commit/3b851cb),
  [36e8dcc](https://github.com/danmichaelo/mwclient/commit/36e8dcc),
  [#19](https://github.com/mwclient/mwclient/pull/19).
* [2013-05-13] [@danmichaelo](https://github.com/danmichaelo):
  Support argument `action` with `logevents()`.
  [241ed37](https://github.com/danmichaelo/mwclient/commit/241ed37),
  [#19](https://github.com/mwclient/mwclient/pull/19).
* [2013-05-13] [@danmichaelo](https://github.com/danmichaelo):
  Support argument `page` with `parse()`.
  [223aa0](https://github.com/danmichaelo/mwclient/commit/223aa0),
  [#19](https://github.com/mwclient/mwclient/pull/19).
* [2013-11-14] [@kyv](https://github.com/kyv):
  Allow setting HTTP `Authorization` header.
  [HTTP headers](http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.8).
  [72fc49a](https://github.com/kyv/mwclient/commit/72fc49a).
* [2013-11-15] [@kyv](https://github.com/kyv):
  Add support for the `ask` API action
  [provided by Semantic MediaWiki](http://semantic-mediawiki.org/wiki/Ask_API).
  [0a16afc](https://github.com/kyv/mwclient/commit/0a16afc).
* [2014-05-02] [@danmichaelo](https://github.com/danmichaelo):
  Quickfix for [#38](https://github.com/mwclient/mwclient/issues/38).
  [98b850b](https://github.com/mwclient/mwclient/commit/98b850b).
* [2014-06-13] [@tuffnatty](https://github.com/tuffnatty):
  Fix updating of Page.last_rev_time upon save().
  [d0cc7db](https://github.com/mwclient/mwclient/commit/d0cc7db),
  [#41](https://github.com/mwclient/mwclient/issues/41).
* [2014-06-13] [@jimt](https://github.com/jimt), [@danmichaelo](https://github.com/danmichaelo):
  Support more arguments to `list=allusers`.
  [7cb4383](https://github.com/mwclient/mwclient/commit/7cb4383),
  [#8](https://github.com/mwclient/mwclient/issues/8).
* [2014-08-18] [@danmichaelo](https://github.com/danmichaelo):
  Replace http.py with the Requests library.
  [593cb44](https://github.com/mwclient/mwclient/commit/593cb44),
  [#45](https://github.com/mwclient/mwclient/issues/45).
* [2014-08-18] [@jaloren](https://github.com/jaloren), [@danmichaelo](https://github.com/danmichaelo):
  Don't crash if edit response does not contain timestamp.
  [bd7bc3b](https://github.com/mwclient/mwclient/commit/bd7bc3b),
  [0ef9a17](https://github.com/mwclient/mwclient/commit/0ef9a17),
  [#57](https://github.com/mwclient/mwclient/issues/57).
* [2014-08-31] [@danmichaelo](https://github.com/danmichaelo):
  Retry on internal_api_error_DBQueryError.
  [d0ce831](https://github.com/mwclient/mwclient/commit/d0ce831).
* [2014-09-22] [@danmichaelo](https://github.com/danmichaelo):
  Rename `Page.edit()` to `Page.text()`. Note that `text` is now a required
  parameter to `Page.save()`.
  [61155f1](https://github.com/mwclient/mwclient/commit/61155f1),
  [#51](https://github.com/mwclient/mwclient/issues/51).
* [2014-09-27] [@danmichaelo](https://github.com/danmichaelo):
  Add `expandtemplates` argument to `Page.text()` and deprecate `Page.get_expanded()`
  [57df5f4](https://github.com/mwclient/mwclient/commit/57df5f4).

## Changes in version 0.6.5
Mwclient 0.6.5 was released on 6 May 2011.
* [2011-02-16] Fix for upload by URL.
  [7ceb14b](https://github.com/mwclient/mwclient/commit/7ceb14b).
* [2011-05-06] Explicitly convert the `Content-Length` header to `str`,
  avoiding a `TypeError` on some versions of Python.
  [4a829bc](https://github.com/mwclient/mwclient/commit/4a829bc),
  [2ca1fbd](https://github.com/mwclient/mwclient/commit/2ca1fbd).
* [2011-05-06] Handle `readapidenied` error in site init.
  [c513396](https://github.com/mwclient/mwclient/commit/c513396).
* [2011-05-06] Fix version parsing for almost any sane version string.
  [9f5339f](https://github.com/mwclient/mwclient/commit/9f5339f).

## Changes in version 0.6.4
Mwclient 0.6.3 was released on 7 April 2010.
* [2009-08-27] Added support for upload API.
  [56eeb9b](https://github.com/mwclient/mwclient/commit/56eeb9b),
  [0d7caab](https://github.com/mwclient/mwclient/commit/0d7caab) (see also
  [610411a](https://github.com/mwclient/mwclient/commit/610411a)).
* [2009-11-02] Added `prop=duplicatefiles`.
  [241e5d6](https://github.com/mwclient/mwclient/commit/241e5d6).
* [2009-11-02] Properly fix detection of alpha versions.
  [241e5d6](https://github.com/mwclient/mwclient/commit/241e5d6).
* [2009-11-14] Added support for built-in JSON library.
  [73e9cd6](https://github.com/mwclient/mwclient/commit/73e9cd6).
* [2009-11-15] Handle badtoken once.
  [4b384e1](https://github.com/mwclient/mwclient/commit/4b384e1).
* [2010-02-23] Fix module conflict with simplejson-1.x
  by inserting mwclient path at the beginning of `sys.path`
  instead of the end.
  [cd37ef0](https://github.com/mwclient/mwclient/commit/cd37ef0).
* [2010-02-23] Fix revision iteration.
  [09b68e9](https://github.com/mwclient/mwclient/commit/09b68e9),
  [2ad32f1](https://github.com/mwclient/mwclient/commit/2ad32f1),
  [afdd5e8](https://github.com/mwclient/mwclient/commit/afdd5e8),
  [993b346](https://github.com/mwclient/mwclient/commit/993b346),
  [#3](https://github.com/mwclient/mwclient/issues/3).
* [2010-04-07] Supply token on login if necessary.
  [3731de5](https://github.com/mwclient/mwclient/commit/3731de5).

## Changes in version 0.6.3
Mwclient 0.6.3 was released on 16 July 2009.
* Added domain parameter to login
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
