import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '../trunk')))

if len(sys.argv) < 3:
	print sys.argv[0], 'username', 'password', '[host=test.wikipedia.org]', '[path=/w/]' 
	sys.exit()
if len(sys.argv) > 3:
	host = sys.argv[3]
else:
	host = 'test.wikipedia.org'
if len(sys.argv) > 4:
	path = sys.argv[4]
else:
	path = '/w/'	


import mwclient
site = mwclient.Site(host, path)
site.version = (1, 17, 'alpha') # Force upload api
site.login(sys.argv[1], sys.argv[2])


f = open('test-image.png', 'rb')

import random
name = ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for i in xrange(8)) + '.png'

print 'Using http://%s%sindex.php?title=File:' % (host, path) + name
print 'Regular upload test'

import pprint
res = site.upload(f, name, 'Regular upload test', ignore = True)
pprint.pprint(res)
assert res['result'] == 'Success'

print 'Overwriting; should give a warning'
res = site.upload(f, name, 'Overwrite upload test')
pprint.pprint(res)
assert res['result'] == 'Warning'
ses = res['sessionkey']

print 'Overwriting with stashed file'
res = site.api('upload', token = site.tokens['edit'], filename = name, sessionkey = ses)
pprint.pprint(res)
assert res['upload']['result'] == 'Warning'
assert 'duplicate' in res['upload']['warnings']
assert 'exists' in res['upload']['warnings']

print 'Uploading empty file; error expected'
from StringIO import StringIO
res = site.upload(StringIO(), name, 'Empty upload test')
pprint.pprint(res)
