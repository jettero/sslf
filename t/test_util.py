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
        time.sleep(0.1)
        with u.RateLimit('10-test', limit=0.2) as rl:
            assert rl == (i%2 == 0)

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
        time.sleep(0.1)
        with u.LogLimit(log, 'test mod(i,2)={}', limit=0.2) as ll:
            ll.debug( i%2 )
    
    assert c['test mod(i,2)=0'] == 5
    assert c['test mod(i,2)=1'] == 0
