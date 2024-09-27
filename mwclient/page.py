import time
from typing import (  # noqa: F401
    Optional, Mapping, Any, cast, Dict, Union, Tuple, Iterable, List
)

import mwclient.errors
import mwclient.listing
from mwclient.types import Namespace
from mwclient.util import parse_timestamp, handle_limit


class Page:
    """
    Represents a page on a MediaWiki wiki represented by a
    :class:`~mwclient.client.Site` object.

    Args:
        site (mwclient.client.Site): The site object this page belongs to.
        name (Union[str, int, Page]): The title of the page, the page ID, or
            another :class:`Page` object to copy.
        info (Optional[dict]): Page info, if already fetched, e.g., when
            iterating over a list of pages. If not provided, the page info
            will be fetched from the API.
        extra_properties (Optional[dict]): Extra properties to fetch when
            initializing the page.

    Examples:
        >>> site = mwclient.Site('en.wikipedia.org')
        >>> page1 = Page(site, 'Main Page')
        >>> page2 = Page(site, 123456)
        >>> page3 = Page(site, 'Main Page', extra_properties={
        ...     'imageinfo': [
        ...         ('iiprop', 'timestamp|user|comment|url|size|sha1|metadata'),
        ...     ],
        ... })
    """

    def __init__(
        self,
        site: 'mwclient.client.Site',
        name: Union[int, str, 'Page'],
        info: Optional[Mapping[str, Any]] = None,
        extra_properties: Optional[Mapping[str, Iterable[Tuple[str, str]]]] = None
    ) -> None:
        if type(name) is type(self):
            self.__dict__.update(name.__dict__)
            return
        self.site = site
        self._textcache = {}  # type: Dict[int, str]

        if not info:
            if extra_properties:
                prop = 'info|' + '|'.join(extra_properties.keys())
                extra_props = []  # type: List[Tuple[str, str]]
                for extra_prop in extra_properties.values():
                    extra_props.extend(extra_prop)
            else:
                prop = 'info'
                extra_props = []

            if type(name) is int:
                info = self.site.get('query', prop=prop, pageids=name,
                                     inprop='protection', *extra_props)
            else:
                info = self.site.get('query', prop=prop, titles=name,
                                     inprop='protection', *extra_props)
            info = next(iter(info['query']['pages'].values()))

        info = cast(Mapping[str, Any], info)
        self._info = info

        if 'invalid' in info:
            raise mwclient.errors.InvalidPageTitle(info.get('invalidreason'))

        self.namespace = info.get('ns', 0)
        self.name = info.get('title', '')
        if self.namespace:
            self.page_title = self.strip_namespace(self.name)
        else:
            self.page_title = self.name

        self.base_title = self.page_title.split('/')[0]
        self.base_name = self.name.split('/')[0]

        self.touched = parse_timestamp(info.get('touched'))
        self.revision = info.get('lastrevid', 0)
        self.exists = 'missing' not in info
        self.length = info.get('length')
        self.protection = {
            i['type']: (i['level'], i.get('expiry'))
            for i in info.get('protection', ())
            if i
        }
        self.redirect = 'redirect' in info
        self.pageid = info.get('pageid', None)
        self.contentmodel = info.get('contentmodel', None)
        self.pagelanguage = info.get('pagelanguage', None)
        self.restrictiontypes = info.get('restrictiontypes', None)

        self.last_rev_time = None  # type: Optional[time.struct_time]
        self.edit_time = None  # type: Optional[time.struct_time]

    def redirects_to(self) -> Optional['Page']:
        """ Get the redirect target page, or None if the page is not a redirect."""
        info = self.site.get('query', prop='pageprops', titles=self.name, redirects='')
        if 'redirects' in info['query']:
            for page in info['query']['redirects']:
                if page['from'] == self.name:
                    return Page(self.site, page['to'])
            return None
        else:
            return None

    def resolve_redirect(self) -> 'Page':
        """ Get the redirect target page, or the current page if its not a redirect."""
        target_page = self.redirects_to()
        if target_page is None:
            return self
        else:
            return target_page

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} object '{self.name}' for {self.site}>"

    @staticmethod
    def strip_namespace(title: str) -> str:
        if title[0] == ':':
            title = title[1:]
        return title[title.find(':') + 1:]

    @staticmethod
    def normalize_title(title: str) -> str:
        # TODO: Make site dependent
        title = title.strip()
        if title[0] == ':':
            title = title[1:]
        title = title[0].upper() + title[1:]
        title = title.replace(' ', '_')
        return title

    def can(self, action: str) -> bool:
        """Check if the current user has the right to carry out some action
        with the current page.

        Example:
            >>> page.can('edit')
            True

        """
        level = self.protection.get(action, (action,))[0]
        if level == 'sysop':
            level = 'editprotected'

        return level in self.site.rights

    def get_token(self, type: str, force: bool = False) -> str:
        return self.site.get_token(type, force, title=self.name)

    def text(
        self,
        section: Union[int, str, None] = None,
        expandtemplates: bool = False,
        cache: bool = True,
        slot: str = 'main'
    ) -> Any:
        """Get the current wikitext of the page, or of a specific section.

        If the page does not exist, an empty string is returned. By
        default, results will be cached and if you call text() again
        with the same section and expandtemplates the result will come
        from the cache. The cache is stored on the instance, so it
        lives as long as the instance does.

        Args:
            section: Section number, to only get text from a single section.
            expandtemplates: Expand templates (default: `False`)
            cache: Use in-memory caching (default: `True`)
        """

        if not self.can('read'):
            raise mwclient.errors.InsufficientPermission(self)
        if not self.exists:
            return ''
        if section is not None:
            section = str(section)

        key = hash((section, expandtemplates))
        if cache and key in self._textcache:
            return self._textcache[key]

        # we set api_chunk_size not max_items because otherwise revisions'
        # default api_chunk_size of 50 gets used and we get 50 revisions;
        # no need to set max_items as well as we only iterate one time
        revs = self.revisions(prop='content|timestamp', api_chunk_size=1, section=section,
                              slots=slot)
        try:
            rev = next(revs)
            if 'slots' in rev:
                text = rev['slots'][slot]['*']
            else:
                text = rev['*']
            self.last_rev_time = rev['timestamp']
        except StopIteration:
            text = ''
            self.last_rev_time = None
        if not expandtemplates:
            self.edit_time = time.gmtime()
        else:
            # The 'rvexpandtemplates' option was removed in MediaWiki 1.32, so we have to
            # make an extra API call, see https://github.com/mwclient/mwclient/issues/214
            text = self.site.expandtemplates(text)

        if cache:
            self._textcache[key] = text
        return text

    def save(self, *args: Tuple[str, Any], **kwargs: Any) -> Any:
        """Alias for edit, for maintaining backwards compatibility."""
        return self.edit(*args, **kwargs)  # type: ignore[arg-type]

    def edit(
        self,
        text: str,
        summary: str = '',
        minor: bool = False,
        bot: bool = True,
        section: Optional[str] = None,
        **kwargs: Any
    ) -> Any:
        """Update the text of a section or the whole page by performing an edit operation.
        """
        return self._edit(summary, minor, bot, section, text=text, **kwargs)

    def append(
        self,
        text: str,
        summary: str = '',
        minor: bool = False,
        bot: bool = True,
        section: Optional[str] = None,
        **kwargs: Any
    ) -> Any:
        """Append text to a section or the whole page by performing an edit operation.
        """
        return self._edit(summary, minor, bot, section, appendtext=text, **kwargs)

    def prepend(
        self,
        text: str,
        summary: str = '',
        minor: bool = False,
        bot: bool = True,
        section: Optional[str] = None,
        **kwargs: Any
    ) -> Any:
        """Prepend text to a section or the whole page by performing an edit operation.
        """
        return self._edit(summary, minor, bot, section, prependtext=text, **kwargs)

    def _edit(
        self, summary: str, minor: bool, bot: bool, section: Optional[str], **kwargs: Any
    ) -> Any:
        if not self.site.logged_in and self.site.force_login:
            raise mwclient.errors.AssertUserFailedError()
        if self.site.blocked:
            raise mwclient.errors.UserBlocked(self.site.blocked)
        if not self.can('edit'):
            raise mwclient.errors.ProtectedPageError(self)

        data = {}
        if minor:
            data['minor'] = '1'
        if not minor:
            data['notminor'] = '1'
        if self.last_rev_time:
            data['basetimestamp'] = time.strftime('%Y%m%d%H%M%S', self.last_rev_time)
        if self.edit_time:
            data['starttimestamp'] = time.strftime('%Y%m%d%H%M%S', self.edit_time)
        if bot:
            data['bot'] = '1'
        if section is not None:
            data['section'] = section

        data.update(kwargs)

        if self.site.force_login:
            data['assert'] = 'user'

        def do_edit() -> Any:
            result = self.site.post('edit', title=self.name, summary=summary,
                                    token=self.get_token('edit'),
                                    **data)
            if result['edit'].get('result').lower() == 'failure':
                raise mwclient.errors.EditError(self, result['edit'])
            return result

        try:
            result = do_edit()
        except mwclient.errors.APIError as e:
            if e.code == 'badtoken':
                # Retry, but only once to avoid an infinite loop
                self.get_token('edit', force=True)
                try:
                    result = do_edit()
                except mwclient.errors.APIError as e2:
                    self.handle_edit_error(e2, summary)
            else:
                self.handle_edit_error(e, summary)

        # 'newtimestamp' is not included if no change was made
        if 'newtimestamp' in result['edit'].keys():
            self.last_rev_time = parse_timestamp(result['edit'].get('newtimestamp'))

        # Workaround for https://phabricator.wikimedia.org/T211233
        for cookie in self.site.connection.cookies:
            if 'PostEditRevision' in cookie.name:
                self.site.connection.cookies.clear(cookie.domain, cookie.path,
                                                   cookie.name)

        # clear the page text cache
        self._textcache = {}
        return result['edit']

    def handle_edit_error(self, e: 'mwclient.errors.APIError', summary: str) -> None:
        if e.code == 'editconflict':
            raise mwclient.errors.EditError(self, summary, e.info)
        elif e.code in {'protectedtitle', 'cantcreate', 'cantcreate-anon',
                        'noimageredirect-anon', 'noimageredirect', 'noedit-anon',
                        'noedit', 'protectedpage', 'cascadeprotected',
                        'customcssjsprotected',
                        'protectednamespace-interface', 'protectednamespace'}:
            raise mwclient.errors.ProtectedPageError(self, e.code, e.info)
        elif e.code == 'assertuserfailed':
            raise mwclient.errors.AssertUserFailedError()
        else:
            raise e

    def touch(self) -> None:
        """Perform a "null edit" on the page to update the wiki's cached data of it.
        This is useful in contrast to purge when needing to update stored data on a wiki,
        for example Semantic MediaWiki properties or Cargo table values, since purge
        only forces update of a page's displayed values and not its store.
        """
        if not self.exists:
            return
        self.append('')

    def move(
        self,
        new_title: str,
        reason: str = '',
        move_talk: bool = True,
        no_redirect: bool = False,
        move_subpages: bool = False,
        ignore_warnings: bool = False
    ) -> Any:
        """Move (rename) page to new_title.

        If user account is an administrator, specify no_redirect as True to not
        leave a redirect.

        If user does not have permission to move page, an InsufficientPermission
        exception is raised.

        API doc: https://www.mediawiki.org/wiki/API:Move
        """
        if not self.can('move'):
            raise mwclient.errors.InsufficientPermission(self)

        data = {}
        if move_talk:
            data['movetalk'] = '1'
        if no_redirect:
            data['noredirect'] = '1'
        if move_subpages:
            data['movesubpages'] = '1'
        if ignore_warnings:
            data['ignorewarnings'] = '1'
        result = self.site.post('move', ('from', self.name), to=new_title,
                                token=self.get_token('move'), reason=reason, **data)
        return result['move']

    def delete(
        self,
        reason: str = '',
        watch: bool = False,
        unwatch: bool = False,
        oldimage: Optional[str] = None
    ) -> Any:
        """Delete page.

        If user does not have permission to delete page, an InsufficientPermission
        exception is raised.

        API doc: https://www.mediawiki.org/wiki/API:Delete
        """
        if not self.can('delete'):
            raise mwclient.errors.InsufficientPermission(self)

        data = {}
        if watch:
            data['watch'] = '1'
        if unwatch:
            data['unwatch'] = '1'
        if oldimage:
            data['oldimage'] = oldimage
        result = self.site.post('delete', title=self.name,
                                token=self.get_token('delete'),
                                reason=reason, **data)
        return result['delete']

    def purge(self) -> None:
        """Purge server-side cache of page. This will re-render templates and other
        dynamic content.

        API doc: https://www.mediawiki.org/wiki/API:Purge
        """
        self.site.post('purge', titles=self.name)

    # def watch: requires 1.14

    # Properties
    def backlinks(
        self,
        namespace: Optional[Namespace] = None,
        filterredir: str = 'all',
        redirect: bool = False,
        limit: Optional[int] = None,
        generator: bool = True,
        max_items: Optional[int] = None,
        api_chunk_size: Optional[int] = None
    ) -> 'mwclient.listing.List':
        """List pages that link to the current page, similar to Special:Whatlinkshere.

        API doc: https://www.mediawiki.org/wiki/API:Backlinks

        """
        (max_items, api_chunk_size) = handle_limit(limit, max_items, api_chunk_size)
        prefix = mwclient.listing.List.get_prefix('bl', generator)
        kwargs = dict(mwclient.listing.List.generate_kwargs(
            prefix, namespace=namespace, filterredir=filterredir,
        ))
        if redirect:
            kwargs[f'{prefix}redirect'] = '1'
        kwargs[prefix + 'title'] = self.name

        return mwclient.listing.List.get_list(generator)(
            self.site, 'backlinks', 'bl', max_items=max_items,
            api_chunk_size=api_chunk_size, return_values='title', **kwargs
        )

    def categories(
        self, generator: bool = True, show: Optional[str] = None
    ) -> Union['mwclient.listing.PagePropertyGenerator', 'mwclient.listing.PageProperty']:
        """List categories used on the current page.

        API doc: https://www.mediawiki.org/wiki/API:Categories

        Args:
            generator: Return generator (Default: True)
            show: Set to 'hidden' to only return hidden categories
                or '!hidden' to only return non-hidden ones.

        Returns:
            mwclient.listings.PagePropertyGenerator
        """
        prefix = mwclient.listing.List.get_prefix('cl', generator)
        kwargs = dict(mwclient.listing.List.generate_kwargs(
            prefix, show=show
        ))

        if generator:
            return mwclient.listing.PagePropertyGenerator(
                self, 'categories', 'cl', **kwargs
            )
        else:
            # TODO: return sortkey if wanted
            return mwclient.listing.PageProperty(
                self, 'categories', 'cl', return_values='title', **kwargs
            )

    def embeddedin(
        self,
        namespace: Optional[Namespace] = None,
        filterredir: str = 'all',
        limit: Optional[int] = None,
        generator: bool = True,
        max_items: Optional[int] = None,
        api_chunk_size: Optional[int] = None
    ) -> 'mwclient.listing.List':
        """List pages that transclude the current page.

        API doc: https://www.mediawiki.org/wiki/API:Embeddedin

        Args:
            namespace Restricts search to a given namespace (Default: None)
            filterredir: How to filter redirects, either 'all' (default),
                'redirects' or 'nonredirects'.
            limit: The API request chunk size (deprecated)
            generator: Return generator (Default: True)
            max_items: The maximum number of pages to yield
            api_chunk_size: The API request chunk size

        Returns:
            mwclient.listings.List: Page iterator
        """
        (max_items, api_chunk_size) = handle_limit(limit, max_items, api_chunk_size)
        prefix = mwclient.listing.List.get_prefix('ei', generator)
        kwargs = dict(mwclient.listing.List.generate_kwargs(prefix, namespace=namespace,
                                                            filterredir=filterredir))
        kwargs[prefix + 'title'] = self.name

        return mwclient.listing.List.get_list(generator)(
            self.site, 'embeddedin', 'ei', max_items=max_items,
            api_chunk_size=api_chunk_size, return_values='title', **kwargs
        )

    def extlinks(self) -> 'mwclient.listing.PageProperty':
        """List external links from the current page.

        API doc: https://www.mediawiki.org/wiki/API:Extlinks

        """
        return mwclient.listing.PageProperty(self, 'extlinks', 'el', return_values='*')

    def images(
        self, generator: bool = True
    ) -> Union['mwclient.listing.PagePropertyGenerator', 'mwclient.listing.PageProperty']:
        """List files/images embedded in the current page.

        API doc: https://www.mediawiki.org/wiki/API:Images

        """
        if generator:
            return mwclient.listing.PagePropertyGenerator(self, 'images', '')
        else:
            return mwclient.listing.PageProperty(self, 'images', '',
                                                 return_values='title')

    def iwlinks(self) -> 'mwclient.listing.PageProperty':
        """List interwiki links from the current page.

        API doc: https://www.mediawiki.org/wiki/API:Iwlinks

        """
        return mwclient.listing.PageProperty(self, 'iwlinks', 'iw',
                                             return_values=('prefix', '*'))

    def langlinks(self, **kwargs: Any) -> 'mwclient.listing.PageProperty':
        """List interlanguage links from the current page.

        API doc: https://www.mediawiki.org/wiki/API:Langlinks

        """
        return mwclient.listing.PageProperty(self, 'langlinks', 'll',
                                             return_values=('lang', '*'),
                                             **kwargs)

    def links(
        self,
        namespace: Optional[Namespace] = None,
        generator: bool = True,
        redirects: bool = False
    ) -> Union['mwclient.listing.PagePropertyGenerator', 'mwclient.listing.PageProperty']:
        """List links to other pages from the current page.

        API doc: https://www.mediawiki.org/wiki/API:Links

        """
        prefix = mwclient.listing.List.get_prefix('pl', generator)
        kwargs = dict(mwclient.listing.List.generate_kwargs(prefix, namespace=namespace))

        if redirects:
            kwargs['redirects'] = '1'
        if generator:
            return mwclient.listing.PagePropertyGenerator(self, 'links', 'pl', **kwargs)
        else:
            return mwclient.listing.PageProperty(self, 'links', 'pl',
                                                 return_values='title', **kwargs)

    def revisions(
        self,
        startid: Optional[int] = None,
        endid: Optional[int] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        dir: str = 'older',
        user: Optional[str] = None,
        excludeuser: Optional[str] = None,
        limit: Optional[int] = None,
        prop: str = 'ids|timestamp|flags|comment|user',
        expandtemplates: bool = False,
        section: Optional[str] = None,
        diffto: Optional[int] = None,
        slots: Optional[str] = None,
        uselang: Optional[str] = None,
        max_items: Optional[int] = None,
        api_chunk_size: Optional[int] = 50
    ) -> 'mwclient.listing.List':
        """List revisions of the current page.

        API doc: https://www.mediawiki.org/wiki/API:Revisions

        Args:
            startid: Revision ID to start listing from.
            endid: Revision ID to stop listing at.
            start: Timestamp to start listing from.
            end: Timestamp to end listing at.
            dir: Direction to list in: 'older' (default) or 'newer'.
            user: Only list revisions made by this user.
            excludeuser: Exclude revisions made by this user.
            limit: The API request chunk size (deprecated).
            prop: Which properties to get for each revision,
                default: 'ids|timestamp|flags|comment|user'
            expandtemplates: Expand templates in rvprop=content output
            section: Section number. If rvprop=content is set, only the contents
                of this section will be retrieved.
            diffto: Revision ID to diff each revision to. Use "prev", "next" and
                "cur" for the previous, next and current revision respectively.
            slots: The content slot (Mediawiki >= 1.32) to retrieve content from.
            uselang: Language to use for parsed edit comments and other localized
                messages.
            max_items: The maximum number of revisions to yield.
            api_chunk_size: The API request chunk size (as a number of revisions).

        Returns:
            mwclient.listings.List: Revision iterator
        """
        (max_items, api_chunk_size) = handle_limit(limit, max_items, api_chunk_size)
        kwargs = dict(mwclient.listing.List.generate_kwargs(
            'rv', startid=startid, endid=endid, start=start, end=end, user=user,
            excludeuser=excludeuser, diffto=diffto, slots=slots
        ))

        if self.site.version[:2] < (1, 32) and 'rvslots' in kwargs:  # type: ignore[index]
            # https://github.com/mwclient/mwclient/issues/199
            del kwargs['rvslots']

        kwargs['rvdir'] = dir
        kwargs['rvprop'] = prop
        kwargs['uselang'] = uselang
        if expandtemplates:
            kwargs['rvexpandtemplates'] = '1'
        if section is not None:
            kwargs['rvsection'] = section

        return mwclient.listing.RevisionsIterator(self, 'revisions', 'rv',
                                                  max_items=max_items,
                                                  api_chunk_size=api_chunk_size,
                                                  **kwargs)

    def templates(
        self, namespace: Optional[Namespace] = None, generator: bool = True
    ) -> Union['mwclient.listing.PagePropertyGenerator', 'mwclient.listing.PageProperty']:
        """List templates used on the current page.

        API doc: https://www.mediawiki.org/wiki/API:Templates

        """
        prefix = mwclient.listing.List.get_prefix('tl', generator)
        kwargs = dict(mwclient.listing.List.generate_kwargs(prefix, namespace=namespace))
        if generator:
            return mwclient.listing.PagePropertyGenerator(self, 'templates', prefix,
                                                          **kwargs)
        else:
            return mwclient.listing.PageProperty(self, 'templates', prefix,
                                                 return_values='title', **kwargs)
