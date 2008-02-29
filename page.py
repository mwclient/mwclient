import client, errors, listing
import compatibility
from HTMLParser import HTMLParser
from htmlentitydefs import name2codepoint 
import urllib, time
	
class Page(object):
	def __init__(self, site, name, info = None, extra_properties = {}):
		if type(name) is type(self):
			return self.__dict__.update(name.__dict__)
		self.site = site
		self.name = name
		
		if not info:
			if extra_properties:
				prop = 'info|' + '|'.join(extra_properties.iterkeys())
				extra_props = []
				[extra_props.extend(extra_prop) for extra_prop in extra_properties.itervalues()]					
			else:
				prop = 'info'
				extra_props = ()
			
			info = self.site.api('query', prop = prop, titles = name, 
				inprop = 'protection', *extra_props)
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
		
		self.edit_time = None
			
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
		if title[0] == ':':
			title[0] = title[1:]
		title = title[0].upper() + title[1:]
		title = title.strip()
		title = title.replace(' ', '_')
		return title

		
	def can(self, action):
		level = self.protection.get(action, (action, ))[0]
		if level == 'sysop': level = compatibility.protectright(site.version)
		
		return level in self.site.rights
		
	def get_token(self, type, force = False):
		self.site.require(1, 11)
		
		if type not in self.site.tokens:
			self.site.tokens[type] = '0'
		if self.site.tokens.get(type, '0') == '0' or force:
			info = self.site.api('query', titles = self.name,
				prop = 'info', intoken = type)
			for i in info['query']['pages'].itervalues():
				if i['title'] == self.name:
					self.site.tokens[type] = i['%stoken' % type]
		return self.site.tokens[type]
		
	def edit(self, section = None, readonly = False):
		if not self.can('read'):
			raise errors.InsufficientPermission(self)
		if not self.exists:
			return u''
			
		revs = self.revisions(prop = 'content|timestamp', limit = 1)
		try:
			rev = revs.next()
			self.text = rev['*']
			self.edit_time = rev['timestamp']
		except StopIteration:
			self.text = u''
			self.edit_time = None
		return self.text
		
	def save(self, text = u'', summary = u'', minor = False):
		if not self.site.logged_in and self.site.force_login:
			# Should we really check for this?
			raise errors.LoginError(self.site)
		if self.site.blocked:
			raise errors.UserBlocked(self.site.blocked)
		if not self.can('edit'):
			raise errors.ProtectedPageError(self)
		
		if not text: text = self.text
		
		data = {}
		data['wpTextbox1'] = text
		data['wpSummary'] = summary
		data['wpSave'] = 'Save page'
		data['wpEditToken'] = self.get_token('edit')
		if self.edit_time:
			data['wpEdittime'] = time.strftime('%Y%m%d%H%M%S', self.edit_time)
		else:
			data['wpEdittime'] = time.strftime('%Y%m%d%H%M%S', time.gmtime())
		data['wpStarttime'] = time.strftime('%Y%m%d%H%M%S', time.gmtime())

		if minor: data['wpMinoredit'] = '1'
		data['title'] = self.name
		
		page_data = self.site.raw_index('submit', **data)
				
		page = EditPage('editform')
		page.feed(page_data)
		page.close()
		
		if page.data:
			if page.readonly: raise errors.ProtectedPageError(self)
			self.get_token('edit',  True)
			raise errors.EditError(page.title, data)
			
	def get_expanded(self):
		self.site.require(1, 12)
		
		revs = self.revisions(prop = 'content', limit = 1, expandtemplates = True)
		try:
			return revs.next()['*']
		except StopIteration:
			return u''
			
	def move(self, new_title, reason = '', move_talk = True):
		if not self.can('move'): raise errors.InsufficientPermission(self)
		
		postdata = {'wpNewTitle': new_title,
			'wpOldTitle': self.name,
			'wpReason': reason,
			'wpMove': '1',
			'wpEditToken': self.get_token('move')}
		if move_talk: postdata['wpMovetalk'] = '1'
		postdata['title'] = 'Special:Movepage'
		
		page_data = self.site.raw_index('submit', **data)
				
		page = EditPage('movepage')
		page.feed(page_data.decode('utf-8', 'ignore'))
		page.close()
		
		if 'wpEditToken' in page.data:
			raise errors.EditError(page.title, postdata)
			
	def delete(self, reason = ''):
		if not self.can('delete'): raise errors.InsufficientPermission(self)
			
		postdata = {'wpReason': reason,
			'wpConfirmB': 'Delete',
			'mw-filedelete-submit': 'Delete',
			'wpEditToken': self.get_token('delete'),
			'title': self.name}
			
		page_data = self.site.raw_index('delete', **data)
		
	def purge(self):
		self.site.raw_index('purge', title = self.name)
		
	# Properties
	def backlinks(self, namespace = None, filterredir = 'all', redirect = False, limit = None, generator = True):
		self.site.require(1, 9)
		# Fix title for < 1.11 !!
		prefix = listing.List.get_prefix('bl', generator)
		kwargs = dict(listing.List.generate_kwargs(prefix, 
			namespace = namespace, filterredir = filterredir))
		if redirect: kwargs['%sredirect' % prefix] = '1'
		kwargs[compatibility.title(prefix, self.site.require(1, 11, raise_error = False))] = self.name
			
		return listing.List.get_list(generator)(self.site, 'backlinks', 'bl', limit = limit, return_values = 'title', **kwargs)
	def categories(self, generator = True):
		self.site.require(1, 11)
		if generator:
			return listing.PagePropertyGenerator(self, 'categories', 'cl')
		else:
			# TODO: return sortkey if wanted
			return listing.PageProperty(self, 'categories', 'cl', return_values = 'title')
	def embeddedin(self, namespace = None, filterredir = 'all', redirect = False, limit = None, generator = True):
		self.site.require(1, 9)
		# Fix title for < 1.11 !!
		prefix = listing.List.get_prefix('ei', generator)
		kwargs = dict(listing.List.generate_kwargs(prefix,
			namespace = namespace, filterredir = filterredir))
		if redirect: kwargs['%sredirect' % prefix] = '1'
		kwargs[compatibility.title(prefix, self.site.require(1, 11, raise_error = False))] = self.name
			
		return listing.List.get_list(generator)(self.site, 'embeddedin', 'ei', limit = limit, return_values = 'title', **kwargs)
	def extlinks(self):
		self.site.require(1, 11)
		return listing.PageProperty(self, 'extlinks', 'el', return_values = '*')
	def images(self, generator = True):
		self.site.require(1, 9)
		if generator:
			return listing.PagePropertyGenerator(self, 'images', '')
		else:
			return listing.PageProperty(self, 'images', '', return_values = 'title')
	def langlinks(self):
		self.site.require(1, 9)
		return listing.PageProperty(self, 'langlinks', 'll', return_values = ('lang', '*'))
	def links(self, namespace = None, generator = True):
		self.site.require(1, 9)
		kwargs = dict(listing.List.generate_kwargs('pl', namespace = namespace))
		if generator:
			return listing.PagePropertyGenerator(self, 'links', 'pl')
		else:
			return listing.PageProperty(self, 'links', 'pl', return_values = 'title')

	def revisions(self, startid = None, endid = None, start = None, end = None, 
			dir = 'older', user = None, excludeuser = None, limit = 50, 
			 prop = 'ids|timestamp|flags|comment|user', expandtemplates = False):
		self.site.require(1, 8)
		kwargs = dict(listing.List.generate_kwargs('rv', startid = startid, endid = endid,
			start = start, end = end, user = user, excludeuser = excludeuser))
		kwargs['rvdir'] = dir
		kwargs['rvprop'] = prop
		if expandtemplates: kwargs['rvexpandtemplates'] = '1'
		
		return listing.PageProperty(self, 'revisions', 'rv', limit = limit, **kwargs)
	def templates(self, namespace = None, generator = True):
		self.site.require(1, 8)
		kwargs = dict(listing.List.generate_kwargs('tl', namespace = namespace))
		if generator:
			return listing.PagePropertyGenerator(self, 'templates', 'tl')
		else:
			return listing.PageProperty(self, 'templates', 'tl', return_values = 'title')

class Image(Page):
	def __init__(self, site, name, info = None):
		site.require(1, 11)
		Page.__init__(self, site, name, info,
			extra_properties = {'imageinfo': (('iiprop', 
				compatibility.iiprop(site.version)), )})
		self.imagerepository = self._info.get('imagerepository', '')
		self.imageinfo = self._info.get('imageinfo', ((), ))[0]

	def imagehistory(self):
		return listing.PageProperty(self, 'imageinfo', 'ii', 
			iiprop = compatibility.iiprop(site.version))
	def imageusage(self, namespace = None, filterredir = 'all', redirect = False, 
			limit = None, generator = True):
		self.site.require(1, 11)
		# TODO: Fix for versions < 1.11
		prefix = listing.List.get_prefix('iu', generator)
		kwargs = dict(listing.List.generate_kwargs(prefix, title = self.name,
			namespace = namespace, filterredir = filterredir))
		if redirect: kwargs['%sredirect' % prefix] = '1'
		return listing.List.get_list(generator)('imageusage', 'iu', limit = limit, return_values = 'title', **kwargs)

	def download(self):
		url = urlparse.urlparse(self.imageinfo[index]['url'])
		# TODO: query string
		return self.site.pool.get(url[1], url[2])
		
	def __repr__(self):
		return "<Image object '%s' for %s>" % (self.name.encode('utf-8'), self.site)
	
class EditPage(HTMLParser):
	def __init__(self, form):
		HTMLParser.__init__(self)
		
		self.form = form
		
		self.in_form = False
		self.in_text = False
		self.in_title = False
		
		self.data = {}
		self.textdata = []
		self.title = u''
		
		self.readonly = True
		
	def handle_starttag(self, tag, attrs):
		self.in_title = (tag == 'title')
		
		if (u'id', self.form) in attrs:
			attrs = dict(attrs)
			self.in_form = True
			self.action = attrs['action']
			
		if tag == 'input' and self.in_form and (u'type', u'submit') \
				not in attrs and (u'type', u'checkbox') not in attrs:
			attrs = dict(attrs)
			if u'name' in attrs: self.data[attrs[u'name']] = attrs.get(u'value', u'')
			
		if self.in_form and tag == 'textarea':
			self.in_text = True
			self.readonly = (u'readonly', u'readonly') in attrs
	
			
	def handle_endtag(self, tag):
		if self.in_title and tag == 'title': self.in_title = False
		if self.in_form and tag == 'form': self.in_form = False
		if self.in_text and tag == 'textarea': self.in_text = False
	
	def handle_data(self, data):
		if self.in_text: self.textdata.append(data)
		if self.in_title: self.title += data
		
	def handle_entityref(self, name):
		if name in name2codepoint: 
			self.handle_data(unichr(name2codepoint[name]))
		else:
			self.handle_data(u'&%s;' % name)
	def handle_charref(self, name):
		try:
			self.handle_data(unichr(int(name)))
		except ValueError:
			self.handle_data(u'&#$s;' % name)
		
