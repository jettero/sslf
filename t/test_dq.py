import pytest
import os

from sslf.util.dq import DiskQueue, MemQueue, DiskBackedQueue
from sslf.util.dq import SSLFQueueTypeError, SSLFQueueCapacityError

TEST_DQ_DIR = os.environ.get('TEST_DQ_DIR', f'/tmp/dq.{os.getuid()}')

@pytest.fixture
def samp():
    return tuple(b'one two three four five'.split())

@pytest.fixture
def mq():
    return MemQueue(size=100)

@pytest.fixture
def dq():
    return DiskQueue(TEST_DQ_DIR, size=100, fresh=True)

@pytest.fixture
def dbq():
    return DiskBackedQueue(TEST_DQ_DIR, mem_size=100, disk_size=100, fresh=True)

def test_mem_queue(mq):
    borked = False

    with pytest.raises(SSLFQueueTypeError):
        mq.put('not work')

    mq.put(b'one')
    mq.put(b'two')
    mq.put(b'three')

    assert len(mq) == 13
    assert mq.peek() == b'one'
    assert mq.get() == b'one'
    assert mq.peek() == b'two'
    assert len(mq) == 9

    assert mq.getz() == b'two three'
    assert len(mq) == 0

    mq.put(b'one')
    mq.put(b'two')
    mq.put(b'three')

    assert mq.getz(8) == b'one two'
    assert mq.getz(8) == b'three'

def test_disk_queue(dq):
    borked = False

    with pytest.raises(SSLFQueueTypeError):
        dq.put('not work')

    dq.put(b'one')
    dq.put(b'two')
    dq.put(b'three')

    assert len(dq) == 13
    assert dq.peek() == b'one'
    assert dq.get() == b'one'
    assert dq.peek() == b'two'
    assert len(dq) == 9

    assert dq.getz() == b'two three'
    assert len(dq) == 0

    dq.put(b'one')
    dq.put(b'two')
    dq.put(b'three')

    assert dq.getz(8) == b'one two'
    assert dq.getz(8) == b'three'

def test_disk_backed_queue(dbq):
    borked = False

    with pytest.raises(SSLFQueueTypeError):
        dbq.put('not work')

    with pytest.raises(SSLFQueueCapacityError):
        for i in range(22):
            dbq.put(f'{i:10}'.encode())

    assert dbq.mq.sz == 100
    assert dbq.dq.sz == 100

    mr,dr = 100,100
    for i in range(20):
        b = f'{i:10}'.encode()
        assert dbq.get() == b

        if dr:
            dr -= 10
        else:
            mr -= 10

        assert dbq.mq.sz == mr
        assert dbq.dq.sz == dr

    assert dbq.mq.sz == 0
    assert dbq.dq.sz == 0

    compare = list()
    for i in range(15):
        v = f'{i:10}'.encode()
        dbq.put(v)
        compare.append(v)
    assert dbq.mq.sz == 100
    assert dbq.dq.sz == 50
    assert dbq.getz() == dbq.mq.sep.join(compare)

    compare = list()
    for i in range(15):
        v = f'{i:10}'.encode()
        dbq.put(v)
        compare.append(v)
    assert dbq.mq.sz == 100
    assert dbq.dq.sz == 50
    assert dbq.getz(25) == dbq.mq.sep.join(compare[0:2])
    compare = compare[2:]
    assert dbq.mq.sz == 100
    assert dbq.dq.sz == 30


def _test_pop(samp,q):
    for i in samp:
        q.put(i)
    for i in samp:
        assert q.peek() == i
        q.pop()

def test_mq_pop(samp,mq):
    _test_pop(samp,mq)

def test_dq_pop(samp,dq):
    _test_pop(samp,dq)

def test_dbq_pop(samp,dbq):
    _test_pop(samp,dbq)
