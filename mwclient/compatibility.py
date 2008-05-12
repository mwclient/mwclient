def title(prefix, new_format):
	if new_format: 
		return prefix + 'title'
	else:
		return 'titles'
		
def userinfo(data, new_format = None):
	if new_format is None:
		# Unknown version; trying to guess
		if 'userinfo' in data: 
			return data['userinfo']
		elif 'userinfo' in data.get('query', ()):
			return data['query']['userinfo']
		else: 
			return {}
	elif new_format:
		return data['query']['userinfo']
	else:
		return data['userinfo']

def iiprop(version):
	if version[:2] >= (1, 13):
		return 'timestamp|user|comment|url|size|sha1|metadata|archivename'
	if version[:2] >= (1, 12):
		return 'timestamp|user|comment|url|size|sha1|metadata'
	else:
		return 'timestamp|user|comment|url|size|sha1'
		
def cmtitle(page, new_format, prefix = ''):
	if new_format:
		return prefix + 'title', page.name
	else:
		return prefix + 'category', page.strip_namespace(page.name)
		
def protectright(version):
	if version[:2] >= (1, 13):
		return 'editprotected'
	else:
		return 'protect'