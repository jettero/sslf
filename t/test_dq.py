import pytest
import os

from sslf.util.dq import DiskQueue, MemQueue, DiskBackedQueue
from sslf.util.dq import SSLFQueueTypeError, SSLFQueueCapacityError

TEST_DQ_DIR = os.environ.get('TEST_DQ_DIR', f'/tmp/dq.{os.getuid()}')

def test_mem_queue():
    mq = MemQueue(size=100)
    borked = False

    with pytest.raises(SSLFQueueTypeError, message="Expecting SSLFQueueTypeError"):
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

def test_disk_queue():
    dq = DiskQueue(TEST_DQ_DIR, size=100, fresh=True)
    borked = False

    with pytest.raises(SSLFQueueTypeError, message="Expecting SSLFQueueTypeError"):
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

def test_dq():
    dq = DQ(TEST_DQ_DIR, mem_size=100, disk_size=100, fresh=True)
    borked = False

    with pytest.raises(SSLFQueueTypeError, message="Expecting SSLFQueueTypeError"):
        dq.put('not work')

    with pytest.raises(SSLFQueueCapacityError, message="Expecting SSLFQueueCapacityError"):
        for i in range(22):
            dq.put(f'{i:10}'.encode())

    assert dq.mq.sz == 100
    assert dq.dq.sz == 100

    mr,dr = 100,100
    for i in range(20):
        b = f'{i:10}'.encode()
        assert dq.get() == b

        if dr:
            dr -= 10
        else:
            mr -= 10

        assert dq.mq.sz == mr
        assert dq.dq.sz == dr

    assert dq.mq.sz == 0
    assert dq.dq.sz == 0
