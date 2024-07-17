from mwclient.util import handle_limit
import mwclient.listing
import mwclient.page


class Image(mwclient.page.Page):

    def __init__(self, site, name, info=None):
        super(Image, self).__init__(
            site, name, info, extra_properties={
                'imageinfo': (
                    ('iiprop',
                     'timestamp|user|comment|url|size|sha1|metadata|mime|archivename'),
                )
            }
        )
        self.imagerepository = self._info.get('imagerepository', '')
        self.imageinfo = self._info.get('imageinfo', ({}, ))[0]

    def imagehistory(self):
        """
        Get file revision info for the given file.

        API doc: https://www.mediawiki.org/wiki/API:Imageinfo
        """
        return mwclient.listing.PageProperty(
            self, 'imageinfo', 'ii',
            iiprop='timestamp|user|comment|url|size|sha1|metadata|mime|archivename'
        )

    def imageusage(self, namespace=None, filterredir='all', redirect=False,
                   limit=None, generator=True, max_items=None, api_chunk_size=None):
        """
        List pages that use the given file.

        API doc: https://www.mediawiki.org/wiki/API:Imageusage
        """
        prefix = mwclient.listing.List.get_prefix('iu', generator)
        kwargs = dict(mwclient.listing.List.generate_kwargs(
            prefix, title=self.name, namespace=namespace, filterredir=filterredir
        ))
        (max_items, api_chunk_size) = handle_limit(limit, max_items, api_chunk_size)
        if redirect:
            kwargs['%sredirect' % prefix] = '1'
        return mwclient.listing.List.get_list(generator)(
            self.site,
            'imageusage',
            'iu',
            max_items=max_items,
            api_chunk_size=api_chunk_size,
            return_values='title',
            **kwargs
        )

    def duplicatefiles(self, limit=None, max_items=None, api_chunk_size=None):
        """
        List duplicates of the current file.

        API doc: https://www.mediawiki.org/wiki/API:Duplicatefiles

        limit sets a hard cap on the total number of results, it does
        not only specify the API chunk size.
        """
        (max_items, api_chunk_size) = handle_limit(limit, max_items, api_chunk_size)
        return mwclient.listing.PageProperty(
            self,
            'duplicatefiles',
            'df',
            max_items=max_items,
            api_chunk_size=api_chunk_size
        )

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
        return "<%s object '%s' for %s>" % (
            self.__class__.__name__,
            self.name,
            self.site
        )
