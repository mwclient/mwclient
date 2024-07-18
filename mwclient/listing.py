from typing import (  # noqa: F401
    Optional, Tuple, Any, Union, Iterator, Mapping, Iterable, Type
)

import mwclient.image
import mwclient.page
from mwclient.types import Namespace
from mwclient.util import parse_timestamp


class List:
    """Base class for lazy iteration over api response content

    This is a class providing lazy iteration.  This means that the
    content is loaded in chunks as long as the response hints at
    continuing content.
    """

    def __init__(
        self,
        site: 'mwclient.client.Site',
        list_name: str,
        prefix: str,
        limit: Optional[int] = None,
        return_values: Union[str, Tuple[str, ...], None] = None,
        max_items: Optional[int] = None,
        *args: Tuple[str, Any],
        **kwargs: Any
    ) -> None:
        # NOTE: Fix limit
        self.site = site
        self.list_name = list_name
        self.generator = 'list'
        self.prefix = prefix

        kwargs.update(args)
        self.args = kwargs

        if limit is None:
            limit = site.api_limit
        self.args[self.prefix + 'limit'] = str(limit)

        self.count = 0
        self.max_items = max_items

        self._iter = iter(range(0))  # type: Iterator[Any]

        self.last = False
        self.result_member = list_name
        self.return_values = return_values

    def __iter__(self) -> 'List':
        return self

    def __next__(self) -> Any:
        if self.max_items is not None:
            if self.count >= self.max_items:
                raise StopIteration

        # For filered lists, we might have to do several requests
        # to get the next element due to miser mode.
        # See: https://github.com/mwclient/mwclient/issues/194
        while True:
            try:
                item = next(self._iter)
                if item is not None:
                    break
            except StopIteration:
                if self.last:
                    raise
                self.load_chunk()

        self.count += 1
        if 'timestamp' in item:
            item['timestamp'] = parse_timestamp(item['timestamp'])

        if isinstance(self, GeneratorList):
            return item
        if type(self.return_values) is tuple:
            return tuple((item[i] for i in self.return_values))
        if self.return_values is not None:
            return item[self.return_values]
        return item

    def load_chunk(self) -> None:
        """Query a new chunk of data

        If the query is empty, `raise StopIteration`.

        Else, update the iterator accordingly.

        If 'continue' is in the response, it is added to `self.args`
        (new style continuation, added in MediaWiki 1.21).

        If not, but 'query-continue' is in the response, query its
        item called `self.list_name` and add this to `self.args` (old
        style continuation).

        Else, set `self.last` to True.
        """
        data = self.site.get(
            'query', (self.generator, self.list_name),
            *[(str(k), v) for k, v in self.args.items()]
        )
        if not data:
            # Non existent page
            raise StopIteration

        # Process response if not empty.
        # See: https://github.com/mwclient/mwclient/issues/194
        if 'query' in data:
            self.set_iter(data)

        if data.get('continue'):
            # New style continuation, added in MediaWiki 1.21
            self.args.update(data['continue'])

        elif self.list_name in data.get('query-continue', ()):
            # Old style continuation
            self.args.update(data['query-continue'][self.list_name])

        else:
            self.last = True

    def set_iter(self, data: Mapping[str, Any]) -> None:
        """Set `self._iter` to the API response `data`."""
        if self.result_member not in data['query']:
            self._iter = iter(range(0))
        elif type(data['query'][self.result_member]) is list:
            self._iter = iter(data['query'][self.result_member])
        else:
            self._iter = iter(data['query'][self.result_member].values())

    def __repr__(self) -> str:
        return "<%s object '%s' for %s>" % (
            self.__class__.__name__,
            self.list_name,
            self.site
        )

    @staticmethod
    def generate_kwargs(
        _prefix: str, *args: Tuple[str, Any], **kwargs: Any
    ) -> Iterable[Tuple[str, Any]]:
        kwargs.update(args)
        for key, value in kwargs.items():
            if value is not None and value is not False:
                yield _prefix + key, value

    @staticmethod
    def get_prefix(prefix: str, generator: bool = False) -> str:
        return ('g' if generator else '') + prefix

    @staticmethod
    def get_list(generator: bool = False) -> Union[Type['GeneratorList'], Type['List']]:
        return GeneratorList if generator else List


class NestedList(List):
    def __init__(self, nested_param: str, *args: Tuple[str, Any], **kwargs: Any) -> None:
        super(NestedList, self).__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.nested_param = nested_param

    def set_iter(self, data: Mapping[str, Any]) -> None:
        self._iter = iter(data['query'][self.result_member][self.nested_param])


class GeneratorList(List):
    """Lazy-loaded list of Page, Image or Category objects

    While the standard List class yields raw response data
    (optionally filtered based on the value of List.return_values),
    this subclass turns the data into Page, Image or Category objects.
    """

    def __init__(
        self,
        site: 'mwclient.client.Site',
        list_name: str,
        prefix: str,
        *args: Tuple[str, Any],
        **kwargs: Any
    ) -> None:
        super(GeneratorList, self).__init__(
            site, list_name, prefix, *args, **kwargs  # type: ignore[arg-type]
        )

        self.args['g' + self.prefix + 'limit'] = self.args[self.prefix + 'limit']
        del self.args[self.prefix + 'limit']
        self.generator = 'generator'

        self.args['prop'] = 'info|imageinfo'
        self.args['inprop'] = 'protection'

        self.result_member = 'pages'

        self.page_class = mwclient.page.Page

    def __next__(self) -> Union['mwclient.page.Page', 'mwclient.image.Image', 'Category']:
        info = super(GeneratorList, self).__next__()
        if info['ns'] == 14:
            return Category(self.site, '', info)
        if info['ns'] == 6:
            return mwclient.image.Image(self.site, '', info)
        return mwclient.page.Page(self.site, '', info)

    def load_chunk(self) -> None:
        # Put this here so that the constructor does not fail
        # on uninitialized sites
        self.args['iiprop'] = 'timestamp|user|comment|url|size|sha1|metadata|archivename'
        return super(GeneratorList, self).load_chunk()


class Category(mwclient.page.Page, GeneratorList):

    def __init__(
        self,
        site: 'mwclient.client.Site',
        name: str,
        info: Optional[Mapping[str, Any]] = None,
        namespace: Optional[Namespace] = None
    ) -> None:
        mwclient.page.Page.__init__(self, site, name, info)
        kwargs = {}
        kwargs['gcmtitle'] = self.name
        if namespace:
            kwargs['gcmnamespace'] = namespace
        GeneratorList.__init__(self, site, 'categorymembers', 'cm', **kwargs)

    def __repr__(self) -> str:
        return "<%s object '%s' for %s>" % (
            self.__class__.__name__,
            self.name,
            self.site
        )

    def members(
        self,
        prop: str = 'ids|title',
        namespace: Optional[Namespace] = None,
        sort: str = 'sortkey',
        dir: str = 'asc',
        start: Optional[str] = None,
        end: Optional[str] = None,
        generator: bool = True
    ) -> 'List':
        prefix = self.get_prefix('cm', generator)
        kwargs = dict(self.generate_kwargs(prefix, prop=prop, namespace=namespace,
                                           sort=sort, dir=dir, start=start, end=end,
                                           title=self.name))
        return self.get_list(generator)(self.site, 'categorymembers', 'cm', **kwargs)


class PageList(GeneratorList):

    def __init__(
        self,
        site: 'mwclient.client.Site',
        prefix: Optional[str] = None,
        start: Optional[str] = None,
        namespace: int = 0,
        redirects: str = 'all',
        end: Optional[str] = None
    ):
        self.namespace = namespace

        kwargs = {}
        if prefix:
            kwargs['gapprefix'] = prefix
        if start:
            kwargs['gapfrom'] = start
        if end:
            kwargs['gapto'] = end

        super(PageList, self).__init__(site, 'allpages', 'ap',
                                       gapnamespace=str(namespace),
                                       gapfilterredir=redirects,
                                       **kwargs)

    def __getitem__(
        self, name: str
    ) -> Union['mwclient.page.Page', 'mwclient.image.Image', 'Category']:
        return self.get(name, None)

    def get(
        self, name: str, info: Optional[Mapping[str, Any]] = None
    ) -> Union['mwclient.page.Page', 'mwclient.image.Image', 'Category']:
        """Return the page of name `name` as an object.

        If self.namespace is not zero, use {namespace}:{name} as the
        page name, otherwise guess the namespace from the name using
        `self.guess_namespace`.

        Returns:
            One of Category, Image or Page (default), according to namespace.
        """
        if self.namespace != 0:
            full_page_name = u"{namespace}:{name}".format(
                namespace=self.site.namespaces[self.namespace],
                name=name,
            )
            namespace = self.namespace
        else:
            full_page_name = name
            try:
                namespace = self.guess_namespace(name)
            except AttributeError:
                # raised when `namespace` doesn't have a `startswith` attribute
                namespace = 0

        cls = {
            14: Category,
            6: mwclient.image.Image,
        }.get(namespace, mwclient.page.Page)

        return cls(self.site, full_page_name, info)  # type: ignore[no-any-return]

    def guess_namespace(self, name: str) -> int:
        """Guess the namespace from name

        If name starts with any of the site's namespaces' names or
        default_namespaces, use that.  Else, return zero.

        Args:
            name: The pagename as a string (having `.startswith`)

        Returns:
            The id of the guessed namespace or zero.
        """
        for ns in self.site.namespaces:
            if ns == 0:
                continue
            namespace = '%s:' % self.site.namespaces[ns].replace(' ', '_')
            if name.startswith(namespace):
                return ns
            elif ns in self.site.default_namespaces:
                namespace = '%s:' % self.site.default_namespaces[ns].replace(' ', '_')
                if name.startswith(namespace):
                    return ns
        return 0


class PageProperty(List):

    def __init__(
        self,
        page: 'mwclient.page.Page',
        prop: str,
        prefix: str,
        *args: Tuple[str, Any],
        **kwargs: Any
    ) -> None:
        super(PageProperty, self).__init__(
            page.site,
            prop,
            prefix,
            titles=page.name,
            *args,  # type: ignore[arg-type]
            **kwargs,
        )
        self.page = page
        self.generator = 'prop'

    def set_iter(self, data: Mapping[str, Any]) -> None:
        for page in data['query']['pages'].values():
            if page['title'] == self.page.name:
                self._iter = iter(page.get(self.list_name, ()))
                return
        raise StopIteration


class PagePropertyGenerator(GeneratorList):

    def __init__(
        self,
        page: 'mwclient.page.Page',
        prop: str,
        prefix: str,
        *args: Tuple[str, Any],
        **kwargs: Any
    ) -> None:
        super(PagePropertyGenerator, self).__init__(page.site, prop, prefix,
                                                    titles=page.name,
                                                    *args, **kwargs)
        self.page = page


class RevisionsIterator(PageProperty):

    def load_chunk(self) -> None:
        if 'rvstartid' in self.args and 'rvstart' in self.args:
            del self.args['rvstart']
        return super(RevisionsIterator, self).load_chunk()
