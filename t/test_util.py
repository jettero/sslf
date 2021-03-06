import sslf.util as u
import time
from collections import Counter

def test_attrdict():
    ad = u.AttrDict()
    ad['supz'] = 7
    assert ad.supz == 7
    ad.yo = 'supz'
    assert ad.get('yo') == None

def _test_attrproxylist(apl):
    assert apl.a ==  7
    assert apl.b ==  8
    assert apl.c ==  9
    assert apl.d == 10

    def plus_one(x):
        return x + 1
    apl.add_lambda(c=plus_one)

    assert apl.a ==  7
    assert apl.b ==  8
    assert apl.c == 10
    assert apl.d == 10
    assert apl.z == None

    def defaultify(x):
        if x is None:
            return 'defaultified'
        return x
    apl.add_lambda(z=defaultify)

    assert apl.z == 'defaultified'

def test_attrproxy_list_class_attrdict():
    class blah:
        a = 7
        b = 8
    bla = blah()
    uad = u.AttrDict(c=9, d=10)
    _test_attrproxylist( u.AttrProxyList(uad, bla) )
    _test_attrproxylist( u.AttrProxyList(bla, uad) )

class mylogger:
    def __init__(self,c=None):
        if c is None:
            c = Counter()
        self.c = c
    def debug(self, fmt, *a, **kw):
        self.c[ fmt.format(*a, **kw) ] += 1
    info = error = debug

def test_ratelimit():
    for i in range(10):
        with u.RateLimit('10-test', limit=0.2) as rl:
            assert bool(rl) == (i%2 == 0)
        time.sleep(0.1)

def test_loglimit():
    c = Counter()
    log = mylogger(c)

    for i in range(10):
        with u.LogLimit(log, 'test mod(i,2)={}', limit=0.2) as ll:
            ll.debug( i%2 )
        time.sleep(0.1)

    assert c['test mod(i,2)=0'] == 5
    assert c['test mod(i,2)=1'] == 0

    for i in (('test-%s',), ('test-%s','two')):
        ll = u.LogLimit(log, *i, limit=0.1)
        assert ll.tag == '|'.join(i)
        assert ll.format == i[0]
        assert ll.dt_ok == True
        time.sleep(0.1)
        assert ll.dt_ok == True
        ll.__exit__()
        assert ll.dt_ok == False
        time.sleep(0.1)
        assert ll.dt_ok == True
        time.sleep(0.1)
        assert ll.dt_ok == True

def test_exception_catcher():
    log = mylogger()
    assert 'supz' not in u.LogLimit.limits
    with u.LogLimit(log, 'supz') as ll:
        ll.debug()
    assert 'supz' in u.LogLimit.limits
    t1 = u.LogLimit.limits['supz']
    with u.LogLimit(log, 'supz') as ll:
        ll.debug()
    t2 = u.LogLimit.limits['supz']
    assert t1 == t2
    with u.LogLimit(log, 'supz', limit=0) as ll:
        ll.debug()
    t3 = u.LogLimit.limits['supz']
    assert t1 != t3
    class broken(Exception):
        pass
    try:
        with u.LogLimit(log, 'supz', limit=0) as ll:
            raise broken("broken")
    except broken:
        pass
    t4 = u.LogLimit.limits['supz']
    assert t4 == t3
