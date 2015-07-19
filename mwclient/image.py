import mwclient.listing
import mwclient.page


class Image(mwclient.page.Page):

    def __init__(self, site, name, info=None):
        mwclient.page.Page.__init__(self, site, name, info,
                                    extra_properties={'imageinfo': (('iiprop', 'timestamp|user|comment|url|size|sha1|metadata|archivename'), )})
        self.imagerepository = self._info.get('imagerepository', '')
        self.imageinfo = self._info.get('imageinfo', ({}, ))[0]

    def imagehistory(self):
        return mwclient.listing.PageProperty(self, 'imageinfo', 'ii',
                                             iiprop='timestamp|user|comment|url|size|sha1|metadata|archivename')

    def imageusage(self, namespace=None, filterredir='all', redirect=False,
                   limit=None, generator=True):
        prefix = mwclient.listing.List.get_prefix('iu', generator)
        kwargs = dict(mwclient.listing.List.generate_kwargs(prefix, title=self.name, namespace=namespace, filterredir=filterredir))
        if redirect:
            kwargs['%sredirect' % prefix] = '1'
        return mwclient.listing.List.get_list(generator)(self.site, 'imageusage', 'iu', limit=limit, return_values='title', **kwargs)

    def duplicatefiles(self, limit=None):
        return mwclient.listing.PageProperty(self, 'duplicatefiles', 'df', dflimit=limit)

    def download(self):
        url = self.imageinfo['url']
        if not url.startswith('http://'):
            url = 'http://' + self.site.host + url
        url = urllib.parse.urlparse(url)
        # TODO: query string
        return self.site.connection.get(url[1], url[2])

    def __repr__(self):
        return "<Image object '%s' for %s>" % (self.name.encode('utf-8'), self.site)
