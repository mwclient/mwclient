__ver__ = '0.6.1'

import urllib, urlparse
import time, random
import sys, weakref
import socket

import simplejson
import http

import errors
import listing, page
import compatibility

try:
	import gzip
except ImportError:
	gzip = None
try:
	from cStringIO import StringIO
except ImportError:
	from StringIO import StringIO

def parse_timestamp(t):
	if t == '0000-00-00T00:00:00Z':
		return (0, 0, 0, 0, 0, 0, 0, 0)
	return time.strptime(t, '%Y-%m-%dT%H:%M:%SZ')
	
class WaitToken(object):
	def __init__(self):
		self.id = '%x' % random.randint(0, sys.maxint)
	def __hash__(self):
		return hash(self.id)

class Site(object):
	api_limit = 500
	def __init__(self, host, path = '/w/', ext = '.php', pool = None, retry_timeout = 30, 
			max_retries = 25, wait_callback = lambda *x: None, 
			max_lag = 3, compress = True, force_login = True, do_init = True):
		self.host = host
		self.path = path
		self.ext = ext
		self.credentials = None
		self.compress = compress
		
		self.retry_timeout = retry_timeout
		self.max_retries = max_retries
		self.wait_callback = wait_callback
		self.max_lag = str(max_lag)
		
		self.wait_tokens = weakref.WeakKeyDictionary()
			
		self.blocked = False
		self.hasmsg = False
		self.groups = []
		self.rights = []
		self.tokens = {}
		self.force_login = force_login
		
		if pool is None:
			self.connection = http.HTTPPool()
		else:
			self.connection = pool
			
		self.version = None
			
		self.Pages = listing.PageList(self)
		self.Categories = listing.PageList(self, namespace = 14)
		self.Images = listing.PageList(self, namespace = 6)
		
		self.namespaces = self.default_namespaces
		self.writeapi = False
		
		self.initialized = False
		
		if do_init:
			try:
				self.site_init()
			except errors.APIError, e:
				# Private wiki, do init after login
				if e[0] != u'unknown_action': raise
				
			
	def site_init(self):
		meta = self.api('query', meta = 'siteinfo|userinfo', 
			siprop = 'general|namespaces', uiprop = 'groups|rights')
		self.site = meta['query']['general']
		self.namespaces = dict(((i['id'], i.get('*', '')) for i in meta['query']['namespaces'].itervalues()))
		self.writeapi = 'writeapi' in self.site
			
		if self.site['generator'].startswith('MediaWiki '):
			version = self.site['generator'][10:].split('.')
			if len(version) == 2 and version[1].endswith('alpha'):
				self.version = (int(version[0]), int(version[1][:-5]), 'alpha')
			elif len(version) == 3:
				self.version = (int(version[0]), int(version[1]), int(version[2]))
			else:
				raise errors.MediaWikiVersionError('Unknown MediaWiki %s' % '.'.join(version))
		else:
			raise errors.MediaWikiVersionError('Unknown generator %s' % self.site['generator'])
		# Require 1.11 until some compatibility issues are fixed
		self.require(1, 11)
			
		userinfo = compatibility.userinfo(meta, self.require(1, 12, raise_error = False))
		self.username = userinfo['name']
		self.groups = userinfo.get('groups', [])
		self.rights = userinfo.get('rights', [])
		self.initialized = True
		
		
	default_namespaces = {0: u'', 1: u'Talk', 2: u'User', 3: u'User talk', 4: u'Project', 5: u'Project talk', 
		6: u'Image', 7: u'Image talk', 8: u'MediaWiki', 9: u'MediaWiki talk', 10: u'Template', 11: u'Template talk', 
		12: u'Help', 13: u'Help talk', 14: u'Category', 15: u'Category talk', -1: u'Special', -2: u'Media'}
		
	def __repr__(self):
		return "<Site object '%s%s'>" % (self.host, self.path)
		
	
	def api(self, action, *args, **kwargs):
		kwargs.update(args)
		if action == 'query':
			if 'meta' in kwargs:
				kwargs['meta'] += '|userinfo'
			else:
				kwargs['meta'] = 'userinfo'
			if 'uiprop' in kwargs:
				kwargs['uiprop'] += '|blockinfo|hasmsg'
			else:
				kwargs['uiprop'] = 'blockinfo|hasmsg'
			
		token = self.wait_token()
		while True:
			info = self.raw_api(action, **kwargs)
			if not info: info = {}
				
			try:
				userinfo = compatibility.userinfo(info, self.require(1, 12, raise_error = None))
			except KeyError:
				userinfo = ()
			if 'blockedby' in userinfo:
				self.blocked = (userinfo['blockedby'], userinfo.get('blockreason', u''))
			else:
				self.blocked = False
			self.hasmsg = 'message' in userinfo
			self.logged_in = 'anon' not in userinfo
			if 'error' in info:
				if info['error']['code'] in (u'internal_api_error_DBConnectionError', ):
					self.wait(token)
					continue
				raise errors.APIError(info['error']['code'],
					info['error']['info'], kwargs)
			return info
		
	@staticmethod
	def _to_str(data):
		if type(data) is unicode:
			return data.encode('utf-8')
		return str(data)
	@staticmethod
	def _query_string(*args, **kwargs):
		kwargs.update(args)
		qs = urllib.urlencode([(k, Site._to_str(v)) for k, v in kwargs.iteritems()
			if k != 'wpEditToken'])
		if 'wpEditToken' in kwargs: 
			qs += '&wpEditToken=' + urllib.quote(Site._to_str(kwargs['wpEditToken']))
		return qs
		
	def raw_call(self, script, data):
		url = self.path + script + self.ext
		headers = {'Content-Type': 'application/x-www-form-urlencoded'}
		if self.compress and gzip:
			headers['Accept-Encoding'] = 'gzip'
		
		token = self.wait_token((script, data))
		while True:
			try:
				stream = self.connection.post(self.host, 
					url, data = data, headers = headers)
				if stream.getheader('Content-Encoding') == 'gzip':
					# BAD.
					seekable_stream = StringIO(stream.read())
					stream = gzip.GzipFile(fileobj = seekable_stream)
				return stream
				
			except errors.HTTPStatusError, e:
				if e[0] == 503 and e[1].getheader('X-Database-Lag'):
					self.wait(token, int(e[1].getheader('Retry-After')))
				elif e[0] < 500 or e[0] > 599:
					raise
				else:
					self.wait(token)
			except errors.HTTPError:
				self.wait(token)
			except ValueError:
				self.wait(token)
				
	def raw_api(self, action, *args, **kwargs):
		kwargs['action'] = action
		kwargs['format'] = 'json'
		data = self._query_string(*args, **kwargs)
		return simplejson.load(self.raw_call('api', data))
				
	def raw_index(self, action, *args, **kwargs):
		kwargs['action'] = action
		kwargs['maxlag'] = self.max_lag
		data = self._query_string(*args, **kwargs)
		return self.raw_call('index', data).read().decode('utf-8', 'ignore')			
				
	def wait_token(self, args = None):
		token = WaitToken()
		self.wait_tokens[token] = (0, args)
		return token
	def wait(self, token, min_wait = 0):
		retry, args = self.wait_tokens[token]
		self.wait_tokens[token] = (retry + 1, args)
		if retry > self.max_retries and self.max_retries != -1:
			raise errors.MaximumRetriesExceeded(self, token, args)
		self.wait_callback(self, token, retry, args)
		
		timeout = self.retry_timeout * retry
		if timeout < min_wait: timeout = min_wait
		time.sleep(timeout)
		return self.wait_tokens[token]

	def require(self, major, minor, revision = None, raise_error = True):
		if self.version is None:
			if raise_error is None: return 
			raise RuntimeError('Site %s has not yet been initialized' % repr(self))
		
		if revision is None:
			if self.version[:2] >= (major, minor):
				return True
			elif raise_error:
				raise errors.MediaWikiVersionError('Requires version %s.%s, current version is %s.%s' 
					% ((major, minor) + self.version[:2]))
			else:
				return False
		else:
			raise NotImplementedError
		

	# Actions
	def email(self, user, text, subject, cc = False):
		postdata = {}
		postdata['wpSubject'] = subject
		postdata['wpText'] = text
		if cc: postdata['wpCCMe'] = '1'
		postdata['wpEditToken'] = self.tokens['edit']
		postdata['uselang'] = 'en'
		postdata['title'] = u'Special:Emailuser/' + user

		data = self.raw_index('submit', postdata)
		if 'var wgAction = "success";' not in data:
			if 'This user has not specified a valid e-mail address' in data:
				# Dirty hack
				raise errors.NoSpecifiedEmailError, user
			raise errors.EmailError, data


	def login(self, username = None, password = None, cookies = None):
		if self.initialized: self.require(1, 10)
		
		if username and password: 
			self.credentials = (username, password)
		if cookies:
			if self.host not in self.conn.cookies:
				self.conn.cookies[self.host] = http.CookieJar()
			self.conn.cookies[self.host].update(cookies)
			
		if self.credentials:
			login = self.api('login', lgname = self.credentials[0], lgpassword = self.credentials[1])
			if login['login']['result'] != 'Success':
				raise errors.LoginError(self, login['login'])
				
		if self.initialized:				
			info = self.api('query', meta = 'userinfo', uiprop = 'groups|rights')
			userinfo = compatibility.userinfo(info, self.require(1, 12, raise_error = False))
			self.username = userinfo['name']
			self.groups = userinfo.get('groups', [])
			self.rights = userinfo.get('rights', [])
			self.tokens = {}
		else:
			self.site_init()


	def upload(self, file, filename, description, license = '', ignore = False, file_size = None): 
		image = self.Images[filename]
		if not image.can('upload'):
			raise errors.InsufficientPermission(filename)
		if image.exists and not ignore:
			raise errors.FileExists(filename)
		
		if type(file) is str:
			file_size = len(file)
			file = StringIO(file)
		if file_size is None:
			file.seek(0, 2)
			file_size = file.tell()
			file.seek(0, 0)
		
		predata = {}
		predata['wpDestFile'] = filename
		predata['wpUploadDescription'] = description
		predata['wpLicense'] = license
		if ignore: predata['wpIgnoreWarning'] = 'true'
		predata['wpUpload'] = 'Upload file'
		predata['wpSourceType'] = 'file'
	
		boundary = '----%s----' % ''.join((random.choice(
			'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') 
			for i in xrange(32)))
		data_header = []
		for name, value in predata.iteritems():
			data_header.append('--' + boundary) 
			data_header.append('Content-Disposition: form-data; name="%s"' % name)
			data_header.append('')
			data_header.append(value.encode('utf-8'))
			
		data_header.append('--' + boundary) 
		data_header.append('Content-Disposition: form-data; name="wpUploadFile"; filename="%s"' % \
			filename.encode('utf-8'))
		data_header.append('Content-Type: application/octet-stream')
		data_header.append('')
		data_header.append('')
		
		postdata = '\r\n'.join(data_header)
		content_length = len(postdata) + file_size + 2 + (4 + len(boundary)) + 2
		
		def iterator():
			yield postdata
			while True:
				chunk = file.read(32768)
				if not chunk: break
				yield chunk
			yield '\r\n'
			yield '--%s--' % boundary
			yield '\r\n'
		
		wait_token = self.wait_token()
		while True:
			try:
				self.connection.post(self.host,
					self.path + 'index.php?title=Special:Upload&maxlag=' + self.max_lag,
					headers = {'Content-Type': 'multipart/form-data; boundary=' + boundary,
						'Content-Length': str(content_length)},
					stream_iter = iterator()).read()
			except errors.HTTPStatusError, e:
				if e[0] == 503 and e[1].getheader('X-Database-Lag'):
					self.wait(wait_token, int(e[1].getheader('Retry-After')))
				elif e[0] < 500 or e[0] > 599:
					raise
				else:
					self.wait(wait_token)
			except errors.HTTPError:
				self.wait(wait_token)
			else:
				return
			file.seek(0, 0)
			
	# Lists
	def allpages(self, start = None, prefix = None, namespace = '0', filterredir = 'all',
			minsize = None, maxsize = None, prtype = None, prlevel = None,
			limit = None, dir = 'ascending', filterlanglinks = 'all', generator = True):
		self.require(1, 9)
		
		pfx = listing.List.get_prefix('ap', generator)
		kwargs = dict(listing.List.generate_kwargs(pfx, ('from', start), prefix = prefix,
			minsize = minsize, maxsize = maxsize, prtype = prtype, prlevel = prlevel,
			namespace = namespace, filterredir = filterredir, dir = dir, 
			filterlanglinks = filterlanglinks))
		return listing.List.get_list(generator)(self, 'allpages', 'ap', limit = limit, return_values = 'title', **kwargs)

	def alllinks(self, start = None, prefix = None, unique = False, prop = 'title',
			namespace = '0', limit = None, generator = True):
		self.require(1, 11)
			
		pfx = listing.List.get_prefix('al', generator)
		kwargs = dict(listing.List.generate_kwargs(pfx, ('from', start), prefix = prefix,
			prop = prop, namespace = namespace))
		if unique: kwargs[pfx + 'unique'] = '1'
		return listing.List.get_list(generator)(self, 'alllinks', 'al', limit = limit, return_values = 'title', **kwargs)

	def allcategories(self, start = None, prefix = None, dir = 'ascending', limit = None, generator = True):
		self.require(1, 12)
		
		pfx = listing.List.get_prefix('ac', generator)
		kwargs = dict(listing.List.generate_kwargs(pfx, ('from', start), prefix = prefix, dir = dir))
		return listing.List.get_list(generator)(self, 'allcategories', 'ac', limit = limit, **kwargs)
	
	def allusers(self, start = None, prefix = None, group = None, prop = None, limit = None):
		self.require(1, 11)
		
		kwargs = dict(listing.List.generate_kwargs('au', ('from', start), prefix = prefix,
			group = group, prop = prop))
		return listing.List(self, 'allusers', 'au', limit = limit, **kwargs)
	def blocks(self, start = None, end = None, dir = 'older', ids = None, users = None, limit = None, 
			prop = 'id|user|by|timestamp|expiry|reason|flags'):
		self.require(1, 12)
		# TODO: Fix. Fix what?
		kwargs = dict(listing.List.generate_kwargs('bk', start = start, end = end, dir = dir, 
			users = users, prop = prop))
		return listing.List(self, 'blocks', 'bk', limit = limit, **kwargs)
	def deletedrevisions(self, start = None, end = None, dir = 'older', namespace = None, 
			limit = None, prop = 'user|comment'):
		# TODO: Fix
		self.require(1, 12)
		
		kwargs = dict(listing.List.generate_kwargs('dr', start = start, end = end, dir = dir,
			namespace = namespace, prop = prop))
		return listing.List(self, 'deletedrevs', 'dr', limit = limit, **kwargs)
	def exturlusage(self, query, prop = None, protocol = 'http', namespace = None, limit = None):
		self.require(1, 11)
		
		kwargs = dict(listing.List.generate_kwargs('eu', query = query, prop = prop, 
			protocol = protocol, namespace = namespace))
		return listing.List(self, 'exturlusage', 'eu', limit = limit, **kwargs)	
	def logevents(self, type = None, prop = None, start = None, end = None, 
			dir = 'older', user = None, title = None, limit = None):
		self.require(1, 9)
		
		kwargs = dict(listing.List.generate_kwargs('le', prop = prop, type = type, start = start,
			end = end, dir = dir, user = user, title = title))
		return listing.List(self, 'logevents', 'le', limit = limit, **kwargs)
	def random(self, namespace, limit = 20):
		self.require(1, 12)
		
		kwargs = dict(listing.List.generate_kwargs('rn', namespace = namespace))
		return listing.List(self, 'random', 'rn', limit = limit, **kwargs)
	
	def recentchanges(self, start = None, end = None, dir = 'older', namespace = None, 
				prop = None, show = None, limit = None, type = None):
		self.require(1, 9)
		
		kwargs = dict(listing.List.generate_kwargs('rc', start = start, end = end, dir = dir,
			namespace = namespace, prop = prop, show = show, type = type))
		return listing.List(self, 'recentchanges', 'rc', limit = limit, **kwargs)
	def search(self, search, namespace = '0', what = 'title', redirects = False, limit = None):
		self.require(1, 11)
		
		kwargs = dict(listing.List.generate_kwargs('sr', search = search, namespace = namespace, what = what))
		if redirects: kwargs['srredirects'] = '1'
		return listing.List(self, 'search', 'sr', limit = limit, **kwargs)
	def usercontributions(self, user, start = None, end = None, dir = 'older', namespace = None, 
			prop = None, show = None, limit = None):
		self.require(1, 9)
		
		kwargs = dict(listing.List.generate_kwargs('uc', user = user, start = start, end = end, 
			dir = dir, namespace = namespace, prop = prop, show = show))
		return listing.List(self, 'usercontribs', 'uc', limit = limit, **kwargs)
	def users(self, users, prop = 'blockinfo|groups|editcount'):
		self.require(1, 12)
		
		return listing.List(self, 'users', 'us', ususers = '|'.join(users), usprop = prop)
		
	def watchlist(self, allrev = False, start = None, end = None, namespace = None, dir = 'older',
			prop = None, show = None, limit = None):
		self.require(1, 9)
		
		kwargs = dict(listing.List.generate_kwargs('wl', start = start, end = end, 
			namespace = namespace, dir = dir, prop = prop, show = show))
		if allrev: kwargs['wlallrev'] = '1'
		return listing.List(self, 'watchlist', 'wl', limit = limit, **kwargs)
		
	def expandtemplates(self, text, title = None, generatexml = False):
		self.require(1, 11)
		
		kwargs = {}
		if title is None: kwargs['title'] = title
		if generatexml: kwargs['generatexml'] = '1'
		
		result = self.api('expandtemplates', text = text, **kwargs)
		
		if generatexml:
			return result['expandtemplates']['*'], result['parsetree']['*']
		else:
			return result['expandtemplates']['*']
		
