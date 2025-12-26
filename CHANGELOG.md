# Changelog for mwclient

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Consolidate material from `REFERENCE.MD` and `README.md` into the
  Sphinx-based docs ([#204](https://github.com/mwclient/mwclient/issues/204)).

- Update the changelog file and make it adher to the https://keepachangelog.com
  convention ([#205](https://github.com/mwclient/mwclient/issues/205)).

- Clean up the exception classes
  ([ad30124](https://github.com/mwclient/mwclient/commit/ad30124),
   [d91ae21](https://github.com/mwclient/mwclient/commit/d91ae21),
   [078cd57](https://github.com/mwclient/mwclient/commit/078cd57)).
   - Changed `AssertUserFailedError` to inherit `MwClientError` rather than `LoginError`,
     since it doesn't have the same args.
   - Changed `AssertUserFailedError` and `InvalidResponse` to store the error message
     in `.args[0]` rather than `.message`.
   - Update `LoginError` so that `OAuthAuthorizationError` is compatible with it.
     While `OAuthAuthorizationError` inherited `LoginError`, they stored
     the args in different ways. They now share the same `.site`, `.code`
     and `.info` properties.

## [0.9.3] - 2018-11-22

### Fixed

- Fix bug introduced in 0.9.2 related to handling the response from multi-content revisions
  ([#199](https://github.com/mwclient/mwclient/issues/199)).

## [0.9.2] - 2018-11-05

### Added

- Add support for the new `slot` parameter to `Page.text()` to support multi content revisions
  under MediaWiki >= 1.32. Defaults to 'main' for backwards compability.
  ([#199](https://github.com/mwclient/mwclient/issues/199))

## [0.9.1] - 2018-07-31

### Added

- Add `show` parameter to `Page.categories()` to allow returning only
  hidden (`show='hidden'`) or non-hidden (`show='!hidden'`) categories.

### Fixed

- Fix handling of empty intermediate responses from miser mode
  ([#194](https://github.com/mwclient/mwclient/issues/194)).

## [0.9.0] - 2018-06-06

### Added

- Add chunked file uploads to allow uploads of larger files
  ([#189](https://github.com/mwclient/mwclient/issues/189)).

### Changed

- Remove support for Python 3.3

## [0.8.7] - 2018-01-14

### Changed

- Raise `InvalidPageTitle` when requesting a page with an invalid title
  ([@automatist](https://github.com/automatist):
   [#183](https://github.com/mwclient/mwclient/issues/183)).

### Fixed

- Include tests in source package
  ([#182](https://github.com/mwclient/mwclient/issues/182)).

- Preserve ordering of JSON results
  ([@JohnGreeley](https://github.com/JohnGreeley):
   [#170](https://github.com/mwclient/mwclient/issues/170)).

- Require pytest-runner only when necessary
  ([@bkuhls](https://github.com/bkuhls):
   [#180](https://github.com/mwclient/mwclient/issues/180)).

## [0.8.6] - 2017-07-31

### Fixed

- Detect, warn and retry on nonce error
  ([@cariaso](https://github.com/cariaso):
   [#165](https://github.com/mwclient/mwclient/issues/165)).

- Fix login on older versions of MediaWiki
  ([@JohnGreeley](https://github.com/JohnGreeley):
   [#166](https://github.com/mwclient/mwclient/issues/166)).

## [0.8.5] - 2017-05-18

### Added

- Add support for fetching tokens from the tokens module for MediaWiki >= 1.27
  ([@ubibene](https://github.com/ubibene) and [@danmichaelo](https://github.com/danmichaelo):
   [#149](https://github.com/mwclient/mwclient/issues/149)).
  - Remove extraneous `continue` parameter from non-query calls
  - Remove `userinfo` from `meta=tokens` calls in order to avoid `readapideniederror` on read protected wikis.

- Pass warnings from the API to the Python logging facility
  ([56cbad3](https://github.com/mwclient/mwclient/commit/56cbad3)).

### Fixed

- Fix Semantic MediaWiki Ask call and response handling
  ([@ubibene](https://github.com/ubibene):
   [#153](https://github.com/mwclient/mwclient/issues/153),
   [#156](https://github.com/mwclient/mwclient/issues/156),
   [#161](https://github.com/mwclient/mwclient/issues/161)).

## [0.8.4] - 2017-02-23

### Changed

- Change `parse` requests to use POST
  ([@bd808](https://github.com/bd808):
   [#147](https://github.com/mwclient/mwclient/issues/147)).

## [0.8.3] - 2016-11-10

### Added

- Add support for sending custom headers with all requests
  ([@bd808](https://github.com/bd808):
   [#143](https://github.com/mwclient/mwclient/issues/143)).


## [0.8.2] - 2016-10-23

### Added

- Add support for passing custom parameters to `requests`
  ([@tosher](https://github.com/tosher):
   [#105](https://github.com/mwclient/mwclient/issues/105)).

- Add `end` argument to `PageList`
  ([@AdamWill](https://github.com/AdamWill):
   [#114](https://github.com/mwclient/mwclient/issues/114)).

- Add `CREDITS.md`
  ([@waldyrious](https://github.com/waldyrious):
   [ebab0e0](https://github.com/mwclient/mwclient/commit/ebab0e0))

- Add <s>`reqs`</s> `requests_args` argument to `Site.__init__`
  ([@tosher](https://github.com/tosher):
   [#105](https://github.com/mwclient/mwclient/issues/105),
   [#119](https://github.com/mwclient/mwclient/issues/119))

- Add OAuth support ([#115](https://github.com/mwclient/mwclient/issues/115))

- Add `assert=user` when `force_login=True`, raise `AssertUserFailedError`
  (subclass of `LoginError`) when assert fails
  ([#125](https://github.com/mwclient/mwclient/issues/125)).

- Add logo
  ([@waldyrious](https://github.com/waldyrious),
   [@c-martinez](https://github.com/c-martinez):
   [#88](https://github.com/mwclient/mwclient/issues/88),
   [#136](https://github.com/mwclient/mwclient/issues/136)).

- Add SSL client certificate as authentication mechanism
  ([@nbareil](https://github.com/nbareil):
   [#139](https://github.com/mwclient/mwclient/issues/139)).

### Changed

- Update [user guide](http://mwclient.readthedocs.io/en/latest/user/)

- Drop Python 2.6 support
  ([@lukasjuhrich](https://github.com/lukasjuhrich):
   [#134](https://github.com/mwclient/mwclient/issues/134))

- Refactoring & code style
  ([@lukasjuhrich](https://github.com/lukasjuhrich):
   [#129](https://github.com/mwclient/mwclient/issues/129),
   [#131](https://github.com/mwclient/mwclient/issues/131))

- Use GET over POST where possible: POST is still the default,
  but GET is used where it's known to work
  ([@cariaso](https://github.com/cariaso),
   [@danmichaelo](https://github.com/danmichaelo):
   [#126](https://github.com/mwclient/mwclient/issues/126))

### Removed

- Remove unused argument `prop` from `Site.allimages()`
  ([524d751](https://github.com/mwclient/mwclient/commit/524d751))

- Remove deprecated method `Page.get_expanded()`
  ([#130](https://github.com/mwclient/mwclient/issues/130))

### Fixed

- Make examples Python 3 compatible
  ([@waldyrious](https://github.com/waldyrious):
  [3345d57](https://github.com/mwclient/mwclient/commit/3345d57))

- Fix argument `prop` for `Site.blocks()`
  ([a148d30](https://github.com/mwclient/mwclient/commit/a148d30))

- Fix `.ask()` method to handle continuation
  ([@cariaso](https://github.com/cariaso):
   [#132](https://github.com/mwclient/mwclient/issues/132))

## [0.8.1] - 2016-02-05

### Added

- Add more options to `Site.parse`
  ([8e729fd](https://github.com/mwclient/mwclient/commit/8e729fd))

### Fixed

- Fix `GeneratorList` with Python 3
  ([@tosher](https://github.com/tosher),
   [@AdamWill](https://github.com/AdamWill):
   [#106](https://github.com/mwclient/mwclient/issues/106))

## [0.8.0] - 2016-02-05

### Added

- Add support for Python 3
  ([#52](https://github.com/mwclient/mwclient/issues/52))

- Cache page text until next edit operation
  ([@AdamWill](https://github.com/AdamWill):
   [#80](https://github.com/mwclient/mwclient/issues/80))

- Add `Site.revisions()` method and support `diffto`
  ([@rdhyee](https://github.com/rdhyee):
   [#84](https://github.com/mwclient/mwclient/issues/84))

### Changed

- *Breaking*: Switch from HTTP to HTTPS as the default.
  See [the user guide](http://mwclient.readthedocs.io/en/latest/user/connecting.html)
  for info on how to still connect using HTTP.
  ([#70](https://github.com/mwclient/mwclient/issues/70))

- *Breaking*:
  Remove implicit use of the `Page.section` attribute when saving, deprecated since 0.7.2
  Saving a section rather than the full page can now only be achieved
  by passing in the `section` parameter explicitly to the `Page.save()` method.
  The section number is no longer part of the `Page` state, so `Page.save()` no longer
  makes use of a section parameter earlier passed into `Page.text()`.
  ([@AdamWill](https://github.com/AdamWill):
   [#81](https://github.com/mwclient/mwclient/issues/81))

### Fixed

- Fix broken `Image.download()` method
  ([038b222](https://github.com/mwclient/mwclient/commits/038b222)).

## [0.7.2] - 2015-07-18

### Added

- Add `continue` parameter to all queries
  ([@c-martinez](https://github.com/c-martinez):
   [#73](https://github.com/mwclient/mwclient/issues/73)).

- Add `toponly` parameter for recentchanges
  ([@itkach](https://github.com/itkach):
   [#78](https://github.com/mwclient/mwclient/issues/78)).

- Add support for querying the CheckUser log
  ([@lfaraone](https://github.com/lfaraone):
   [#86](https://github.com/mwclient/mwclient/issues/86)).

- Expose `pageid`, `contentmodel`, `pagelanguage`, `restrictiontypes` as attributes of `Page`
  ([@PierreSelim](https://github.com/PierreSelim):
   [#89](https://github.com/mwclient/mwclient/issues/89)).

### Changed

- Deprecate implicit use of `Page.section` when saving, to prepare for the merge of
  [#81](https://github.com/mwclient/mwclient/issues/81).

- More intuitive error message when an invalid JSON response is received
  ([#79](https://github.com/mwclient/mwclient/issues/79)).

### Fixed

- Fix prefixing of PageList API argument passing to GeneratorList
  ([@AdamWill](https://github.com/AdamWill):
   [059322e](https://github.com/mwclient/mwclient/commits/059322e)).

- Configure default logger
  ([@Gui13](https://github.com/Gui13):
   [#82](https://github.com/mwclient/mwclient/issues/82)).

- Fix 'New messages' flag (`hasmsg`)
  ([@Pathoschild](https://github.com/Pathoschild):
   [#90](https://github.com/mwclient/mwclient/issues/90)).

- Don't retry on connection error during site init
  ([#85](https://github.com/mwclient/mwclient/issues/85)).

## [0.7.1] - 2014-12-19

### Added

- Implement `Site.allimages()`
  ([@jimt](https://github.com/jimt):
   [#62](https://github.com/mwclient/mwclient/issues/62))

- Support new token handling system
  ([#64](https://github.com/mwclient/mwclient/issues/64))

### Changed

- Update email method to use API
  ([e9572e1](https://github.com/mwclient/mwclient/commits/e9572e1))

- Use 'simplified' continuation
  ([#66](https://github.com/mwclient/mwclient/issues/66))

- Use Basic/Digest Auth from Requests
  ([8bec560](https://github.com/mwclient/mwclient/commits/8bec560))

### Fixed

- Fix so [maxlag](https://www.mediawiki.org/wiki/Manual:Maxlag_parameter)
  is handled correctly

- Fix filtering of page links by namespace
  ([@c-martinez](https://github.com/c-martinez):
   [#72](https://github.com/mwclient/mwclient/issues/72))

- Fix uploading files with non-ascii characters in filenames
  ([#65](https://github.com/mwclient/mwclient/issues/65))

## [0.7.0] - 2014-09-27

### Upgrade notices

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

### Detailed changelog

- Allow setting both the upload description and the page content separately
  ([@btongminh](https://github.com/btongminh):
   [0aa748f](https://github.com/mwclient/mwclient/commit/0aa748f))

- Improve documentation
  ([@tommorris](https://github.com/tommorris):
   [a2723e7](https://github.com/mwclient/mwclient/commit/a2723e7))

- Converted the repository to git and moved from sourceforge to github
  ([@waldyrious](https://github.com/waldyrious):
   [#1](https://github.com/mwclient/mwclient/issues/1), also
   [#11](https://github.com/mwclient/mwclient/issues/11),
   [#13](https://github.com/mwclient/mwclient/issues/13),
   [#15](https://github.com/mwclient/mwclient/issues/15))

- Support for customising the useragent
  ([@eug48](https://github.com/eug48):
   [#16](https://github.com/mwclient/mwclient/pull/16))

- Removed unused `Request` class
  ([@eug48](https://github.com/eug48):
   [#16](https://github.com/mwclient/mwclient/pull/16))

- Support for requesting pages by their page id (`site.pages[page_id]`)
  ([@danmichaelo](https://github.com/danmichaelo):
   [#19](https://github.com/mwclient/mwclient/pull/19))

- Support for editing sections
  ([@danmichaelo](https://github.com/danmichaelo):
   [#19](https://github.com/mwclient/mwclient/pull/19))

- New method `Page.redirects_to()` and helper method `Page.resolve_redirect()`
  ([@danmichaelo](https://github.com/danmichaelo):
  [#19](https://github.com/mwclient/mwclient/pull/19))

- Support argument `action` with `logevents()`
  ([@danmichaelo](https://github.com/danmichaelo):
  [#19](https://github.com/mwclient/mwclient/pull/19))

- Support argument `page` with `parse()`
  ([@danmichaelo](https://github.com/danmichaelo):
  [#19](https://github.com/mwclient/mwclient/pull/19))

- Allow setting HTTP `Authorization` header
  [HTTP headers](http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.8).
  ([@kyv](https://github.com/kyv):
  [72fc49a](https://github.com/kyv/mwclient/commit/72fc49a))

- Add support for the `ask` API action
  [provided by Semantic MediaWiki](http://semantic-mediawiki.org/wiki/Ask_API)
  ([@kyv](https://github.com/kyv):
  [0a16afc](https://github.com/kyv/mwclient/commit/0a16afc))

- Quickfix for [#38](https://github.com/mwclient/mwclient/issues/38)
  ([@danmichaelo](https://github.com/danmichaelo):
   [98b850b](https://github.com/mwclient/mwclient/commit/98b850b))

- Fix updating of `Page.last_rev_time` upon `save()`
  ([@tuffnatty](https://github.com/tuffnatty):
   [#41](https://github.com/mwclient/mwclient/issues/41))

- Support more arguments to `list=allusers`
  ([@jimt](https://github.com/jimt),
   [@danmichaelo](https://github.com/danmichaelo):
   [#8](https://github.com/mwclient/mwclient/issues/8))

- Replace http.py with the Requests library
  ([@danmichaelo](https://github.com/danmichaelo):
   [#45](https://github.com/mwclient/mwclient/issues/45))

- Don't crash if edit response does not contain timestamp
  ([@jaloren](https://github.com/jaloren),
   [@danmichaelo](https://github.com/danmichaelo):
   [#57](https://github.com/mwclient/mwclient/issues/57))

- Retry on internal_api_error_DBQueryError
  ([@danmichaelo](https://github.com/danmichaelo):
   [d0ce831](https://github.com/mwclient/mwclient/commit/d0ce831))

- Rename `Page.edit()` to `Page.text()`. Note that `text` is now a required
  parameter to `Page.save()`.
  ([@danmichaelo](https://github.com/danmichaelo):
   [#51](https://github.com/mwclient/mwclient/issues/51))

- Add `expandtemplates` argument to `Page.text()` and deprecate `Page.get_expanded()`
  ([@danmichaelo](https://github.com/danmichaelo):
   [57df5f4](https://github.com/mwclient/mwclient/commit/57df5f4))

## [0.6.5] - 2011-05-06

- Fix for upload by URL.
  [7ceb14b](https://github.com/mwclient/mwclient/commit/7ceb14b).
- Explicitly convert the `Content-Length` header to `str`,
  avoiding a `TypeError` on some versions of Python.
  [4a829bc](https://github.com/mwclient/mwclient/commit/4a829bc),
  [2ca1fbd](https://github.com/mwclient/mwclient/commit/2ca1fbd).
- Handle `readapidenied` error in site init.
  [c513396](https://github.com/mwclient/mwclient/commit/c513396).
- Fix version parsing for almost any sane version string.
  [9f5339f](https://github.com/mwclient/mwclient/commit/9f5339f).

## [0.6.4] - 2010-04-07

- [2009-08-27] Added support for upload API.
  [56eeb9b](https://github.com/mwclient/mwclient/commit/56eeb9b),
  [0d7caab](https://github.com/mwclient/mwclient/commit/0d7caab) (see also
  [610411a](https://github.com/mwclient/mwclient/commit/610411a)).
- [2009-11-02] Added `prop=duplicatefiles`.
  [241e5d6](https://github.com/mwclient/mwclient/commit/241e5d6).
- [2009-11-02] Properly fix detection of alpha versions.
  [241e5d6](https://github.com/mwclient/mwclient/commit/241e5d6).
- [2009-11-14] Added support for built-in JSON library.
  [73e9cd6](https://github.com/mwclient/mwclient/commit/73e9cd6).
- [2009-11-15] Handle badtoken once.
  [4b384e1](https://github.com/mwclient/mwclient/commit/4b384e1).
- [2010-02-23] Fix module conflict with simplejson-1.x
  by inserting mwclient path at the beginning of `sys.path`
  instead of the end.
  [cd37ef0](https://github.com/mwclient/mwclient/commit/cd37ef0).
- [2010-02-23] Fix revision iteration.
  [09b68e9](https://github.com/mwclient/mwclient/commit/09b68e9),
  [2ad32f1](https://github.com/mwclient/mwclient/commit/2ad32f1),
  [afdd5e8](https://github.com/mwclient/mwclient/commit/afdd5e8),
  [993b346](https://github.com/mwclient/mwclient/commit/993b346),
  [#3](https://github.com/mwclient/mwclient/issues/3).
- [2010-04-07] Supply token on login if necessary.
  [3731de5](https://github.com/mwclient/mwclient/commit/3731de5).

## [0.6.3] - 2009-07-16

- Added domain parameter to login
- Applied edit fix to `page_nowriteapi`
- Allow arbitrary data to be passed to `page.save`
- Fix mwclient on WMF wikis

## 0.6.2 - 2009-05-02

- Compatibility fixes for MediaWiki 1.13
- Download fix for images
- Full support for editing pages via write API
  and split of compatibility to another file.
- Added `expandtemplates` API call
- Added and fixed moving via API
- Raise an `ApiDisabledError` if the API is disabled
- Added support for HTTPS
- Fixed email code
- Mark edits as bots by default.
- Added `action=parse`. Modified patch by Brian Mingus.
- Improved general HTTP and upload handling.

## 0.6.1 - 2008-05

Mwclient 0.6.1 was released in May 2008.
No release notes were kept for this version.

## 0.6.0 - 2008-02

Mwclient 0.6.0 was released in February 2008.
This was the first official release via Sourceforge.
This version removed some Pywikipedia influences added in 0.4.

## 0.5

Mwclient 0.5 was an architectural redesign
which accomplished easy extendability
and added proper support for continuations.

## 0.4

Mwclient 0.4 was somewhat the basis for future releases
and shows the current module architecture.
It was influenced by Pywikipedia,
which was discovered by the author at the time.

## 0.2 and 0.3

Mwclient 0.2 and 0.3 were probably a bit of a generalization,
and maybe already used the API for some part,
but details are unknown.

## 0.1

Mwclient 0.1 was a non-API module for accessing Wikipedia using an XML parser.


[Unreleased]: https://github.com/mwclient/mwclient/compare/v0.9.3...HEAD
[0.9.3]: https://github.com/mwclient/mwclient/compare/v0.9.2...v0.9.3
[0.9.2]: https://github.com/mwclient/mwclient/compare/v0.9.1...v0.9.2
[0.9.1]: https://github.com/mwclient/mwclient/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/mwclient/mwclient/compare/v0.8.7...v0.9.0
[0.8.7]: https://github.com/mwclient/mwclient/compare/v0.8.6...v0.8.7
[0.8.6]: https://github.com/mwclient/mwclient/compare/v0.8.5...v0.8.6
[0.8.5]: https://github.com/mwclient/mwclient/compare/v0.8.4...v0.8.5
[0.8.4]: https://github.com/mwclient/mwclient/compare/v0.8.3...v0.8.4
[0.8.3]: https://github.com/mwclient/mwclient/compare/v0.8.2...v0.8.3
[0.8.2]: https://github.com/mwclient/mwclient/compare/v0.8.1...v0.8.2
[0.8.1]: https://github.com/mwclient/mwclient/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/mwclient/mwclient/compare/v0.7.2...v0.8.0
[0.7.2]: https://github.com/mwclient/mwclient/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/mwclient/mwclient/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/mwclient/mwclient/compare/REL_0_6_5...v0.7.0
[0.6.5]: https://github.com/mwclient/mwclient/compare/REL_0_6_4...REL_0_6_5
[0.6.4]: https://github.com/mwclient/mwclient/compare/REL_0_6_3...REL_0_6_4
[0.6.3]: https://github.com/mwclient/mwclient/compare/REL_0_6_2...REL_0_6_3
