import io
from typing import Optional, Mapping, Any, overload

import mwclient.listing
import mwclient.page
from mwclient.types import Namespace


class Image(mwclient.page.Page):

    def __init__(
        self,
        site: 'mwclient.client.Site',
        name: str,
        info: Optional[Mapping[str, Any]] = None
    ) -> None:
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

    def imagehistory(self) -> 'mwclient.listing.PageProperty':
        """
        Get file revision info for the given file.

        API doc: https://www.mediawiki.org/wiki/API:Imageinfo
        """
        return mwclient.listing.PageProperty(
            self, 'imageinfo', 'ii',
            iiprop='timestamp|user|comment|url|size|sha1|metadata|mime|archivename'
        )

    def imageusage(
        self,
        namespace: Optional[Namespace] = None,
        filterredir: str = 'all',
        redirect: bool = False,
        limit: Optional[int] = None,
        generator: bool = True
    ) -> 'mwclient.listing.List':
        """
        List pages that use the given file.

        API doc: https://www.mediawiki.org/wiki/API:Imageusage
        """
        prefix = mwclient.listing.List.get_prefix('iu', generator)
        kwargs = dict(mwclient.listing.List.generate_kwargs(
            prefix, title=self.name, namespace=namespace, filterredir=filterredir
        ))
        if redirect:
            kwargs['%sredirect' % prefix] = '1'
        return mwclient.listing.List.get_list(generator)(
            self.site, 'imageusage', 'iu', limit=limit, return_values='title', **kwargs
        )

    def duplicatefiles(
        self, limit: Optional[int] = None
    ) -> 'mwclient.listing.PageProperty':
        """
        List duplicates of the current file.

        API doc: https://www.mediawiki.org/wiki/API:Duplicatefiles
        """
        return mwclient.listing.PageProperty(self, 'duplicatefiles', 'df', dflimit=limit)

    @overload
    def download(self) -> bytes:
        ...

    @overload
    def download(self, destination: io.BufferedWriter) -> None:
        ...

    def download(
        self, destination: Optional[io.BufferedWriter] = None
    ) -> Optional[bytes]:
        """
        Download the file. If `destination` is given, the file will be written
        directly to the stream. Otherwise the file content will be stored in memory
        and returned (with the risk of running out of memory for large files).

        Recommended usage:

            >>> with open(filename, 'wb') as fd:
            ...     image.download(fd)

        Args:
            destination: Destination file
        """
        url = self.imageinfo['url']
        if destination is not None:
            res = self.site.connection.get(url, stream=True)
            for chunk in res.iter_content(1024):
                destination.write(chunk)
            return None
        else:
            return self.site.connection.get(url).content

    def __repr__(self) -> str:
        return "<%s object '%s' for %s>" % (
            self.__class__.__name__,
            self.name,
            self.site
        )
