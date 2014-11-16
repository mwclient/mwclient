import client
import errors
import listing

from six.moves import urllib
from six import text_type
import time
import warnings


class Page(object):

    def __init__(self, site, name, info=None, extra_properties={}):
        if type(name) is type(self):
            return self.__dict__.update(name.__dict__)
        self.site = site
        self.name = name
        self.section = None

        if not info:
            if extra_properties:
                prop = 'info|' + '|'.join(extra_properties.iterkeys())
                extra_props = []
                [extra_props.extend(extra_prop) for extra_prop in extra_properties.itervalues()]
            else:
                prop = 'info'
                extra_props = ()

            if type(name) is int:
                info = self.site.api('query', prop=prop, pageids=name,
                                     inprop='protection', *extra_props)
            else:
                info = self.site.api('query', prop=prop, titles=name,
                                     inprop='protection', *extra_props)
            info = info['query']['pages'].itervalues().next()
        self._info = info

        self.namespace = info.get('ns', 0)
        self.name = info.get('title', u'')
        if self.namespace:
            self.page_title = self.strip_namespace(self.name)
        else:
            self.page_title = self.name

        self.touched = client.parse_timestamp(info.get('touched', '0000-00-00T00:00:00Z'))
        self.revision = info.get('lastrevid', 0)
        self.exists = 'missing' not in info
        self.length = info.get('length')
        self.protection = dict([(i['type'], (i['level'], i['expiry'])) for i in info.get('protection', ()) if i])
        self.redirect = 'redirect' in info

        self.last_rev_time = None
        self.edit_time = None

    def redirects_to(self):
        """ Returns the redirect target page, or None if the page is not a redirect page."""
        info = self.site.api('query', prop='pageprops', titles=self.name, redirects='')['query']
        if 'redirects' in info:
            for page in info['redirects']:
                if page['from'] == self.name:
                    return Page(self.site, page['to'])
            return None
        else:
            return None

    def resolve_redirect(self):
        """ Returns the redirect target page, or the current page if it's not a redirect page."""
        target_page = self.redirects_to()
        if target_page is None:
            return self
        else:
            return target_page

    def __repr__(self):
        return "<Page object '%s' for %s>" % (self.name.encode('utf-8'), self.site)

    def __unicode__(self):
        return self.name

    @staticmethod
    def strip_namespace(title):
        if title[0] == ':':
            title = title[1:]
        return title[title.find(':') + 1:]

    @staticmethod
    def normalize_title(title):
        # TODO: Make site dependent
        title = title.strip()
        if title[0] == ':':
            title = title[1:]
        title = title[0].upper() + title[1:]
        title = title.replace(' ', '_')
        return title

    def can(self, action):
        level = self.protection.get(action, (action, ))[0]
        if level == 'sysop':
            level = 'editprotected'

        return level in self.site.rights

    def get_token(self, type, force=False):
        return self.site.get_token(type, force, title=self.name)

    def get_expanded(self):
        """Deprecated. Use page.text(expandtemplates=True) instead"""
        warnings.warn("page.get_expanded() was deprecated in mwclient 0.7.0, use page.text(expandtemplates=True) instead.",
                      category=DeprecationWarning, stacklevel=2)

        return self.text(expandtemplates=True)

    def edit(self, *args, **kwargs):
        """Deprecated. Use page.text() instead"""
        warnings.warn("page.edit() was deprecated in mwclient 0.7.0, please use page.text() instead.",
                      category=DeprecationWarning, stacklevel=2)
        return self.text(*args, **kwargs)

    def text(self, section=None, expandtemplates=False):
        """
        Returns the current wikitext of the page, or of a specific section.
        If the page does not exist, an empty string is returned.

        :Arguments:
          - `section` : numbered section or `None` to get the whole page (default: `None`)
          - `expandtemplates` : set to `True` to expand templates (default: `False`)
        """

        if not self.can('read'):
            raise errors.InsufficientPermission(self)
        if not self.exists:
            return u''
        if section is not None:
            section = text_type(section)

        revs = self.revisions(prop='content|timestamp', limit=1, section=section, expandtemplates=expandtemplates)
        try:
            rev = revs.next()
            text = rev['*']
            self.section = section
            self.last_rev_time = rev['timestamp']
        except StopIteration:
            text = u''
            self.section = None
            self.last_rev_time = None
        if not expandtemplates:
            self.edit_time = time.gmtime()
        return text

    def save(self, text, summary=u'', minor=False, bot=True, section=None, **kwargs):
        """
        Update the text of a section or the whole page by performing an edit operation.
        """
        if not self.site.logged_in and self.site.force_login:
            # Should we really check for this?
            raise errors.LoginError(self.site, 'By default, mwclient protects you from accidentally ' +
                                    'editing without being logged in. If you actually want to edit without '
                                    'logging in, you can set force_login on the Site object to False.')
        if self.site.blocked:
            raise errors.UserBlocked(self.site.blocked)
        if not self.can('edit'):
            raise errors.ProtectedPageError(self)

        if not section:
            section = self.section

        if not self.site.writeapi:
            raise errors.NoWriteApi(self)

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
        if section:
            data['section'] = section

        data.update(kwargs)

        def do_edit():
            result = self.site.api('edit', title=self.name, text=text,
                                   summary=summary, token=self.get_token('edit'),
                                   **data)
            if result['edit'].get('result').lower() == 'failure':
                raise errors.EditError(self, result['edit'])
            return result
        try:
            result = do_edit()
        except errors.APIError as e:
            if e.code == 'badtoken':
                # Retry, but only once to avoid an infinite loop
                self.get_token('edit', force=True)
                try:
                    result = do_edit()
                except errors.APIError as e:
                    self.handle_edit_error(e, summary)
            else:
                self.handle_edit_error(e, summary)

        # 'newtimestamp' is not included if no change was made
        if 'newtimestamp' in result['edit'].keys():
            self.last_rev_time = client.parse_timestamp(result['edit'].get('newtimestamp'))
        return result['edit']

    def handle_edit_error(self, e, summary):
        if e.code == 'editconflict':
            raise errors.EditError(self, summary, e.info)
        elif e.code in ('protectedtitle', 'cantcreate', 'cantcreate-anon', 'noimageredirect-anon',
                        'noimageredirect', 'noedit-anon', 'noedit'):
            raise errors.ProtectedPageError(self, e.code, e.info)
        else:
            raise

    def move(self, new_title, reason='', move_talk=True, no_redirect=False):
        """Move (rename) page to new_title.

        If user account is an administrator, specify no_direct as True to not
        leave a redirect.

        If user does not have permission to move page, an InsufficientPermission
        exception is raised.

        """
        if not self.can('move'):
            raise errors.InsufficientPermission(self)

        if not self.site.writeapi:
            raise errors.NoWriteApi(self)

        data = {}
        if move_talk:
            data['movetalk'] = '1'
        if no_redirect:
            data['noredirect'] = '1'
        result = self.site.api('move', ('from', self.name), to=new_title,
                               token=self.get_token('move'), reason=reason, **data)
        return result['move']

    def delete(self, reason='', watch=False, unwatch=False, oldimage=False):
        """Delete page.

        If user does not have permission to delete page, an InsufficientPermission
        exception is raised.

        """
        if not self.can('delete'):
            raise errors.InsufficientPermission(self)

        if not self.site.writeapi:
            raise errors.NoWriteApi(self)

        data = {}
        if watch:
            data['watch'] = '1'
        if unwatch:
            data['unwatch'] = '1'
        if oldimage:
            data['oldimage'] = oldimage
        result = self.site.api('delete', title=self.name,
                               token=self.get_token('delete'),
                               reason=reason, **data)
        return result['delete']

    def purge(self):
        """Purge server-side cache of page. This will re-render templates and other
        dynamic content.

        """
        self.site.raw_index('purge', title=self.name)

    # def watch: requires 1.14

    # Properties
    def backlinks(self, namespace=None, filterredir='all', redirect=False, limit=None, generator=True):
        prefix = listing.List.get_prefix('bl', generator)
        kwargs = dict(listing.List.generate_kwargs(prefix,
                                                   namespace=namespace, filterredir=filterredir))
        if redirect:
            kwargs['%sredirect' % prefix] = '1'
        kwargs[prefix + 'title'] = self.name

        return listing.List.get_list(generator)(self.site, 'backlinks', 'bl', limit=limit, return_values='title', **kwargs)

    def categories(self, generator=True):
        if generator:
            return listing.PagePropertyGenerator(self, 'categories', 'cl')
        else:
            # TODO: return sortkey if wanted
            return listing.PageProperty(self, 'categories', 'cl', return_values='title')

    def embeddedin(self, namespace=None, filterredir='all', redirect=False, limit=None, generator=True):
        prefix = listing.List.get_prefix('ei', generator)
        kwargs = dict(listing.List.generate_kwargs(prefix,
                                                   namespace=namespace, filterredir=filterredir))
        if redirect:
            kwargs['%sredirect' % prefix] = '1'
        kwargs[prefix + 'title'] = self.name

        return listing.List.get_list(generator)(self.site, 'embeddedin', 'ei', limit=limit, return_values='title', **kwargs)

    def extlinks(self):
        return listing.PageProperty(self, 'extlinks', 'el', return_values='*')

    def images(self, generator=True):
        if generator:
            return listing.PagePropertyGenerator(self, 'images', '')
        else:
            return listing.PageProperty(self, 'images', '', return_values='title')

    def iwlinks(self):
        return listing.PageProperty(self, 'iwlinks', 'iw', return_values=('prefix', '*'))

    def langlinks(self, **kwargs):
        return listing.PageProperty(self, 'langlinks', 'll', return_values=('lang', '*'), **kwargs)

    def links(self, namespace=None, generator=True, redirects=False):
        prefix = listing.List.get_prefix('pl', generator)
        kwargs = dict(listing.List.generate_kwargs(prefix, namespace=namespace))

        if redirects:
            kwargs['redirects'] = '1'
        if generator:
            return listing.PagePropertyGenerator(self, 'links', 'pl', **kwargs)
        else:
            return listing.PageProperty(self, 'links', 'pl', return_values='title', **kwargs)

    def revisions(self, startid=None, endid=None, start=None, end=None,
                  dir='older', user=None, excludeuser=None, limit=50,
                  prop='ids|timestamp|flags|comment|user', expandtemplates=False, section=None):
        kwargs = dict(listing.List.generate_kwargs('rv', startid=startid, endid=endid,
                                                   start=start, end=end, user=user, excludeuser=excludeuser))
        kwargs['rvdir'] = dir
        kwargs['rvprop'] = prop
        if expandtemplates:
            kwargs['rvexpandtemplates'] = '1'
        if section is not None:
            kwargs['rvsection'] = section

        return listing.RevisionsIterator(self, 'revisions', 'rv', limit=limit, **kwargs)

    def templates(self, namespace=None, generator=True):
        kwargs = dict(listing.List.generate_kwargs('tl', namespace=namespace))
        if generator:
            return listing.PagePropertyGenerator(self, 'templates', 'tl')
        else:
            return listing.PageProperty(self, 'templates', 'tl', return_values='title')


class Image(Page):

    def __init__(self, site, name, info=None):
        Page.__init__(self, site, name, info,
                      extra_properties={'imageinfo':
                                        (('iiprop', 'timestamp|user|comment|url|size|sha1|metadata|archivename'), )
                                        })
        self.imagerepository = self._info.get('imagerepository', '')
        self.imageinfo = self._info.get('imageinfo', ({}, ))[0]

    def imagehistory(self):
        return listing.PageProperty(self, 'imageinfo', 'ii',
                                    iiprop='timestamp|user|comment|url|size|sha1|metadata|archivename')

    def imageusage(self, namespace=None, filterredir='all', redirect=False,
                   limit=None, generator=True):
        prefix = listing.List.get_prefix('iu', generator)
        kwargs = dict(listing.List.generate_kwargs(prefix, title=self.name,
                                                   namespace=namespace, filterredir=filterredir))
        if redirect:
            kwargs['%sredirect' % prefix] = '1'
        return listing.List.get_list(generator)(self.site, 'imageusage', 'iu',
                                                limit=limit, return_values='title', **kwargs)

    def duplicatefiles(self, limit=None):
        return listing.PageProperty(self, 'duplicatefiles', 'df',
                                    dflimit=limit)

    def download(self):
        url = self.imageinfo['url']
        if not url.startswith('http://'):
            url = 'http://' + self.site.host + url
        url = urllib.parse.urlparse(url)
        # TODO: query string
        return self.site.connection.get(url[1], url[2])

    def __repr__(self):
        return "<Image object '%s' for %s>" % (self.name.encode('utf-8'), self.site)
