def title(prefix, compatible):
	if compatible: 
		return 'title'
	else:
		return prefix + 'title'
		
def userinfo(data, new_format):
	if new_format:
		return data['query']['userinfo']
	else:
		return data['userinfo']
