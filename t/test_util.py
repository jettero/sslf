import SplunkSuperLightForwarder.util as u
import time
from collections import Counter

def test_attrdict():
    ad = u.AttrDict()
    ad['supz'] = 7
    assert ad.supz == 7
    ad.yo = 'supz'
    assert ad.get('yo') == None

def test_ratelimit():
    for i in range(10):
        with u.RateLimit('10-test', limit=0.2) as rl:
            assert bool(rl) == (i%2 == 0)
        time.sleep(0.1)

def test_loglimit():
    class mylogger(object):
        def __init__(self,c):
            self.c = c
        def debug(self, fmt, *a, **kw):
            self.c[ fmt.format(*a, **kw) ] += 1
        info = error = debug

    c = Counter()
    log = mylogger(c)

    for i in range(10):
        with u.LogLimit(log, 'test mod(i,2)={}', limit=0.2) as ll:
            ll.debug( i%2 )
        time.sleep(0.1)

    assert c['test mod(i,2)=0'] == 5
    assert c['test mod(i,2)=1'] == 0

    for i in (('test-%s',), ('test-%s','two')):
        ll = u.LogLimit(log, *i)
        assert ll.tag == '|'.join(i)
        assert ll.format == i[0]
