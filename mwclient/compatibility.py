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

def iiprop(post_112):
	if post_112:
		return 'timestamp|user|comment|url|size|sha1|metadata'
	else:
		return 'timestamp|user|comment|url|size|sha1'