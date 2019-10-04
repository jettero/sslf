import pytest
import os

from sslf.util.dq import DiskQueue, MemQueue, DiskBackedQueue
from sslf.util.dq import SSLFQueueTypeError, SSLFQueueCapacityError

TEST_DQ_DIR = os.environ.get('TEST_DQ_DIR', f'/tmp/dq.{os.getuid()}')

@pytest.fixture
def mq():
    return MemQueue(size=100)

@pytest.fixture
def dq():
    return DiskQueue(TEST_DQ_DIR, size=100, fresh=True)

@pytest.fixture
def dbq():
    return DiskBackedQueue(TEST_DQ_DIR, mem_size=50, disk_size=50, fresh=True)

def _fill_q_with_samples(q, samp):
    item_count, byte_count = 0, 0
    with pytest.raises(SSLFQueueCapacityError):
        for s in samp:
            q.put(s)
            item_count += 1
            byte_count += len(s)
    return item_count, byte_count

def _test_q_with_samples(q, samp):
    item_count, byte_count = _fill_q_with_samples(q, samp)

    assert q.cn == item_count
    assert q.sz == byte_count
    assert q.peek() == samp[0]
    assert q.get()  == samp[0]
    assert q.peek() == samp[1]
    assert q.get()  == samp[1]
    assert q.cn == item_count - 2
    assert q.sz == byte_count - len(samp[0]) - len(samp[1])

    hrm = b''
    for i in samp[2:]:
        if len(hrm) + 1 + len(i) > 100:
            break
        if hrm:
            hrm += b' '
        hrm += i

    assert q.getz(sz=100) == hrm
    assert q.cn == 0

    q.put(b'one')
    q.put(b'two')
    q.put(b'three')

    assert q.getz(8) == b'one two'
    assert q.getz(8) == b'three'
    assert q.cn == 0

    blah = b'this is huge' * 20
    assert len(blah) > 100
    with pytest.raises(SSLFQueueCapacityError):
        q.put(blah)

    assert q.cn == 0

def test_mem_queue(mq, b_samp):
    with pytest.raises(SSLFQueueTypeError):
        mq.put('not work')

    _test_q_with_samples(mq, b_samp)

def test_disk_queue(dq, b_samp):
    with pytest.raises(SSLFQueueTypeError):
        dq.put('not work')

    _test_q_with_samples(dq, b_samp)

def test_disk_backed_queue(dbq, b_samp):
    with pytest.raises(SSLFQueueTypeError):
        dbq.put('not work')

    _test_q_with_samples(dbq, b_samp)
    _fill_q_with_samples(dbq, b_samp)

    assert dbq.mq.sz <= 50
    assert dbq.dq.sz <= 50
    assert dbq.mq.sz > 10
    assert dbq.dq.sz > 10

def _test_pop(q, samp, do_also=None):
    _fill_q_with_samples(q, samp)
    for i in samp:
        assert q.peek() == i
        q.pop()
        if callable(do_also):
            do_also()
        if q.cn < 1:
            break

def test_mq_pop(mq, b_samp):
    _test_pop(mq, b_samp)

def test_dq_pop(dq, b_samp):
    _test_pop(dq, b_samp)

def test_dbq_pop(dbq, b_samp):
    def check_cn():
        assert dbq.dq.cn + dbq.mq.cn == dbq.cn
    _test_pop(dbq, b_samp, check_cn)
