import sys
import os
import pprint

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '../')))
import mwclient


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


site = mwclient.Site(host, path)
site.login(sys.argv[1], sys.argv[2])


import random
name = ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for i in xrange(8)) + '.png'

print 'Using http://%s%sindex.php?title=File:' % (host, path) + name
print 'Regular upload test'

res = site.upload(open('test-image.png', 'rb'), name, 'Regular upload test', ignore=True)
pprint.pprint(res)
assert res['result'] == 'Success'
assert 'exists' not in res['warnings']

print 'Overwriting; should give a warning'
res = site.upload(open('test-image.png', 'rb'), name, 'Overwrite upload test')
pprint.pprint(res)
assert res['result'] == 'Warning'
assert 'exists' in res['warnings']

ses = res['sessionkey']

print 'Overwriting with stashed file'
res = site.upload(filename=name, session_key=ses)
pprint.pprint(res)
assert res['result'] == 'Warning'
assert 'duplicate' in res['warnings']
assert 'exists' in res['warnings']

print 'Uploading empty file; error expected'
from StringIO import StringIO
res = site.upload(StringIO(), name, 'Empty upload test')
