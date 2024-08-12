import io
from typing import Optional, Mapping, Any, overload

import mwclient.listing
import mwclient.page
from mwclient.types import Namespace
from mwclient.util import handle_limit


class Image(mwclient.page.Page):
    """
    Represents an image on a MediaWiki wiki represented by a
    :class:`~mwclient.client.Site` object.

    Args:
        site (mwclient.client.Site): The site object this page belongs to.
        name (Union[str, int, Page]): The title of the page, the page ID, or
            another :class:`Page` object to copy.
        info (Optional[dict]): Page info, if already fetched, e.g., when
            iterating over a list of pages. If not provided, the page info
            will be fetched from the API.
    """

    def __init__(
        self,
        site: 'mwclient.client.Site',
        name: str,
        info: Optional[Mapping[str, Any]] = None
    ) -> None:
        super().__init__(
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
        generator: bool = True,
        max_items: Optional[int] = None,
        api_chunk_size: Optional[int] = None
    ) -> 'mwclient.listing.List':
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
            kwargs[f'{prefix}redirect'] = '1'
        return mwclient.listing.List.get_list(generator)(
            self.site,
            'imageusage',
            'iu',
            max_items=max_items,
            api_chunk_size=api_chunk_size,
            return_values='title',
            **kwargs
        )

    def duplicatefiles(
        self,
        limit: Optional[int] = None,
        max_items: Optional[int] = None,
        api_chunk_size: Optional[int] = None
    ) -> 'mwclient.listing.PageProperty':
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
        return f"<{self.__class__.__name__} object '{self.name}' for {self.site}>"
