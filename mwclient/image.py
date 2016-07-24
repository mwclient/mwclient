import mwclient.listing
import mwclient.page


class Image(mwclient.page.Page):

    def __init__(self, site, name, info=None):
        super(Image, self).__init__(site, name, info,
                                    extra_properties={'imageinfo': (('iiprop', 'timestamp|user|comment|url|size|sha1|metadata|archivename'), )})
        self.imagerepository = self._info.get('imagerepository', '')
        self.imageinfo = self._info.get('imageinfo', ({}, ))[0]

    def imagehistory(self):
        """
        Get file revision info for the given file.

        API doc: https://www.mediawiki.org/wiki/API:Imageinfo
        """
        return mwclient.listing.PageProperty(self, 'imageinfo', 'ii',
                                             iiprop='timestamp|user|comment|url|size|sha1|metadata|archivename')

    def imageusage(self, namespace=None, filterredir='all', redirect=False,
                   limit=None, generator=True):
        """
        List pages that use the given file.

        API doc: https://www.mediawiki.org/wiki/API:Imageusage
        """
        prefix = mwclient.listing.List.get_prefix('iu', generator)
        kwargs = dict(mwclient.listing.List.generate_kwargs(prefix, title=self.name, namespace=namespace, filterredir=filterredir))
        if redirect:
            kwargs['%sredirect' % prefix] = '1'
        return mwclient.listing.List.get_list(generator)(self.site, 'imageusage', 'iu', limit=limit, return_values='title', **kwargs)

    def duplicatefiles(self, limit=None):
        """
        List duplicates of the current file.

        API doc: https://www.mediawiki.org/wiki/API:Duplicatefiles
        """
        return mwclient.listing.PageProperty(self, 'duplicatefiles', 'df', dflimit=limit)

    def download(self, destination=None):
        """
        Download the file. If `destination` is given, the file will be written
        directly to the stream. Otherwise the file content will be stored in memory
        and returned (with the risk of running out of memory for large files).

        Recommended usage:

            >>> with open(filename, 'wb') as fd:
            ...     image.download(fd)

        Args:
            destination (file object): Destination file
        """
        url = self.imageinfo['url']
        if destination is not None:
            res = self.site.connection.get(url, stream=True)
            for chunk in res.iter_content(1024):
                destination.write(chunk)
        else:
            return self.site.connection.get(url).content

    def __repr__(self):
        return "<Image object '%s' for %s>" % (self.name.encode('utf-8'), self.site)
