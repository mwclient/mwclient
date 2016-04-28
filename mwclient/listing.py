import six
import six.moves
from six import text_type
from mwclient.util import parse_timestamp
import mwclient.page
import mwclient.image


class List(object):

    def __init__(self, site, list_name, prefix, limit=None, return_values=None, max_items=None, *args, **kwargs):
        # NOTE: Fix limit
        self.site = site
        self.list_name = list_name
        self.generator = 'list'
        self.prefix = prefix

        kwargs.update(args)
        self.args = kwargs

        if limit is None:
            limit = site.api_limit
        self.args[self.prefix + 'limit'] = text_type(limit)

        self.count = 0
        self.max_items = max_items

        self._iter = iter(six.moves.range(0))

        self.last = False
        self.result_member = list_name
        self.return_values = return_values

    def __iter__(self):
        return self

    def __next__(self, full=False):
        if self.max_items is not None:
            if self.count >= self.max_items:
                raise StopIteration
        try:
            item = six.next(self._iter)
            self.count += 1
            if 'timestamp' in item:
                item['timestamp'] = parse_timestamp(item['timestamp'])
            if full:
                return item

            if type(self.return_values) is tuple:
                return tuple((item[i] for i in self.return_values))
            elif self.return_values is None:
                return item
            else:
                return item[self.return_values]

        except StopIteration:
            if self.last:
                raise StopIteration
            self.load_chunk()
            return List.__next__(self, full=full)

    def next(self, full=False):
        """ For Python 2.x support """
        return self.__next__(full)

    def load_chunk(self):
        data = self.site.api('query', (self.generator, self.list_name), *[(text_type(k), v) for k, v in six.iteritems(self.args)])
        if not data:
            # Non existent page
            raise StopIteration
        self.set_iter(data)

        if data.get('continue'):
            # New style continuation, added in MediaWiki 1.21
            self.args.update(data['continue'])

        elif self.list_name in data.get('query-continue', ()):
            # Old style continuation
            self.args.update(data['query-continue'][self.list_name])

        else:
            self.last = True

    def set_iter(self, data):
        if self.result_member not in data['query']:
            self._iter = iter(six.moves.range(0))
        elif type(data['query'][self.result_member]) is list:
            self._iter = iter(data['query'][self.result_member])
        else:
            self._iter = six.itervalues(data['query'][self.result_member])

    def __repr__(self):
        return "<List object '%s' for %s>" % (self.list_name, self.site)

    @staticmethod
    def generate_kwargs(_prefix, *args, **kwargs):
        kwargs.update(args)
        for key, value in six.iteritems(kwargs):
            if value is not None and value is not False:
                yield _prefix + key, value

    @staticmethod
    def get_prefix(prefix, generator=False):
        if generator:
            return 'g' + prefix
        else:
            return prefix

    @staticmethod
    def get_list(generator=False):
        if generator:
            return GeneratorList
        else:
            return List


class NestedList(List):
    def __init__(self, nested_param, *args, **kwargs):
        List.__init__(self, *args, **kwargs)
        self.nested_param = nested_param

    def set_iter(self, data):
        self._iter = iter(data['query'][self.result_member][self.nested_param])


class GeneratorList(List):

    def __init__(self, site, list_name, prefix, *args, **kwargs):
        List.__init__(self, site, list_name, prefix, *args, **kwargs)

        self.args['g' + self.prefix + 'limit'] = self.args[self.prefix + 'limit']
        del self.args[self.prefix + 'limit']
        self.generator = 'generator'

        self.args['prop'] = 'info|imageinfo'
        self.args['inprop'] = 'protection'

        self.result_member = 'pages'

        self.page_class = mwclient.page.Page

    def __next__(self):
        info = List.__next__(self, full=True)
        if info['ns'] == 14:
            return Category(self.site, u'', info)
        if info['ns'] == 6:
            return mwclient.image.Image(self.site, u'', info)
        return mwclient.page.Page(self.site, u'', info)

    def next(self):
        """ For Python 2.x support """
        return self.__next__()

    def load_chunk(self):
        # Put this here so that the constructor does not fail
        # on uninitialized sites
        self.args['iiprop'] = 'timestamp|user|comment|url|size|sha1|metadata|archivename'
        return List.load_chunk(self)


class Category(mwclient.page.Page, GeneratorList):

    def __init__(self, site, name, info=None, namespace=None):
        mwclient.page.Page.__init__(self, site, name, info)
        kwargs = {}
        kwargs['gcmtitle'] = self.name
        if namespace:
            kwargs['gcmnamespace'] = namespace
        GeneratorList.__init__(self, site, 'categorymembers', 'cm', **kwargs)

    def __repr__(self):
        return "<Category object '%s' for %s>" % (self.name.encode('utf-8'), self.site)

    def members(self, prop='ids|title', namespace=None, sort='sortkey',
                dir='asc', start=None, end=None, generator=True):
        prefix = self.get_prefix('cm', generator)
        kwargs = dict(self.generate_kwargs(prefix, prop=prop, namespace=namespace,
                                           sort=sort, dir=dir, start=start, end=end, title=self.name))
        return self.get_list(generator)(self.site, 'categorymembers', 'cm', **kwargs)


class PageList(GeneratorList):

    def __init__(self, site, prefix=None, start=None, namespace=0, redirects='all', end=None):
        self.namespace = namespace

        kwargs = {}
        if prefix:
            kwargs['gapprefix'] = prefix
        if start:
            kwargs['gapfrom'] = start
        if end:
            kwargs['gapto'] = end

        GeneratorList.__init__(self, site, 'allpages', 'ap',
                               gapnamespace=text_type(namespace), gapfilterredir=redirects, **kwargs)

    def __getitem__(self, name):
        return self.get(name, None)

    def get(self, name, info=()):
        if self.namespace == 14:
            return Category(self.site, self.site.namespaces[14] + ':' + name, info)
        elif self.namespace == 6:
            return mwclient.image.Image(self.site, self.site.namespaces[6] + ':' + name, info)
        elif self.namespace != 0:
            return mwclient.page.Page(self.site, self.site.namespaces[self.namespace] + ':' + name, info)
        else:
            # Guessing page class
            if type(name) is not int:
                namespace = self.guess_namespace(name)
                if namespace == 14:
                    return Category(self.site, name, info)
                elif namespace == 6:
                    return mwclient.image.Image(self.site, name, info)
            return mwclient.page.Page(self.site, name, info)

    def guess_namespace(self, name):
        for ns in self.site.namespaces:
            if ns == 0:
                continue
            if name.startswith(u'%s:' % self.site.namespaces[ns].replace(' ', '_')):
                return ns
            elif ns in self.site.default_namespaces:
                if name.startswith(u'%s:' % self.site.default_namespaces[ns].replace(' ', '_')):
                    return ns
        return 0


class PageProperty(List):

    def __init__(self, page, prop, prefix, *args, **kwargs):
        List.__init__(self, page.site, prop, prefix, titles=page.name, *args, **kwargs)
        self.page = page
        self.generator = 'prop'

    def set_iter(self, data):
        for page in six.itervalues(data['query']['pages']):
            if page['title'] == self.page.name:
                self._iter = iter(page.get(self.list_name, ()))
                return
        raise StopIteration


class PagePropertyGenerator(GeneratorList):

    def __init__(self, page, prop, prefix, *args, **kwargs):
        GeneratorList.__init__(self, page.site, prop, prefix, titles=page.name, *args, **kwargs)
        self.page = page


class RevisionsIterator(PageProperty):

    def load_chunk(self):
        if 'rvstartid' in self.args and 'rvstart' in self.args:
            del self.args['rvstart']
        return PageProperty.load_chunk(self)
