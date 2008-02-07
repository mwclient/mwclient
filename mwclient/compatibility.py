def title(prefix, new_format):
	if new_format: 
		return prefix + 'title'
	else:
		return 'titles'
		
def userinfo(data, new_format):
	if new_format:
		return data['query']['userinfo']
	else:
		return data['userinfo']
