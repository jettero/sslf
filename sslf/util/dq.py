# coding: utf-8

import os
import logging
import time
import shutil
import errno
from collections import deque

__all__ = [
    'SSLFQueueTypeError', 'SSLFQueueCapacityError', 'MemQueue', 'DiskQueue',
    'DiskBackedQueue', 'DEFAULT_MEMORY_SIZE', 'DEFAULT_DISK_SIZE',
]

log = logging.getLogger(__name__)

OK_TYPES = (bytes,bytearray,)
K_ = 1024
M_ = K_ ** 2
SPLUNK_MAX_MSG      = 100 * K_
DEFAULT_MEMORY_SIZE = 500 * K_
DEFAULT_DISK_SIZE   = 5 * M_

class SSLFQueueTypeError(Exception):
    pass

class SSLFQueueCapacityError(Exception):
    pass

class OKTypesMixin:
    def __init__(self, ok_types=OK_TYPES):
        self.init_types(ok_types)

    def init_types(self, ok_types):
        self.ok_types = ok_types

    def check_type(self, item):
        if not isinstance(item, self.ok_types):
            raise SSLFQueueTypeError(f'type({type(item)}) is not ({self.ok_types})')


class MemQueue(OKTypesMixin):
    sep = b' '

    def __init__(self, size=DEFAULT_MEMORY_SIZE, ok_types=OK_TYPES):
        self.init_types(ok_types)
        self.init_mq(size)

    def init_mq(self, size):
        self.size = size
        # compose rather than inherit to limit operations to append()/popleft() and
        # ignore the rest of the deque() functionality
        self.mq = deque()

    def accept(self, item):
        ''' Decide if the given item will fit in the queue '''
        if len(item) + self.sz > self.size:
            return False
        return True

    def put(self, item):
        ''' append item to the queue '''
        self.check_type(item)
        if not self.accept(item):
            raise SSLFQueueCapacityError('refusing to accept item due to size')
        self.mq.append(item)

    def unget(self, item):
        ''' put this item back in the front of the queue (woopsie?) '''
        self.check_type(item)
        self.mq.appendleft(item)

    def get(self):
        ''' pop next item and return it, ignore if queue is empty (returning None) '''
        if len(self.mq) > 0:
            return self.mq.popleft()

    def pop(self):
        ''' pop next item without returning it '''
        self.get()

    def getz(self, sz=SPLUNK_MAX_MSG):
        ''' pop elements from the stack and combine (with separators when
            necessary) until param sz is reached

            special case: if the very first element is larger than sz, return
            it anyway to prevent getting stuck.
        '''
        r = b''
        while len(self.mq) > 0 and len(r) + len(self.sep) + len(self.peek()) < sz:
            if r:
                r += self.sep
            r += self.mq.popleft()
        if not r:
            return self.get()
        return r

    def peek(self):
        ''' if there's elements in the memqueue, return the first one without popping from the stack '''
        if len(self.mq) > 0:
            return self.mq[0]

    @property
    def sz(self):
        ''' bytes in queue '''
        s = 0
        for i in self.mq:
            s += len(i)
        return s

    @property
    def cn(self):
        ''' items in queue '''
        return len(self.mq)

    @property
    def msz(self):
        ''' size of queue in bytes including separators '''
        return self.sz + max(0, len(self.sep) * (self.cn -1))

    def __len__(self):
        ''' see: msz property '''
        return self.msz


class DiskQueue(OKTypesMixin):
    sep = b' '

    def __init__(self, directory, size=DEFAULT_DISK_SIZE, ok_types=OK_TYPES, fresh=False):
        self.init_types(ok_types)
        self.init_dq(directory, size)
        if fresh:
            self.clear()
        self._count()

    def init_dq(self, directory, size):
        self.directory = directory
        self.size = size

    def _mkdir(self, partial=None):
        d = self.directory
        if partial is not None:
            d = os.path.join(d, partial)
        if not os.path.isdir(d):
            try: os.makedirs(d)
            except OSError as e:
                if e.errno == errno.EEXIST and os.path.isdir(d): pass
                else: raise
        return d

    def clear(self):
        if os.path.isdir(self.directory):
            shutil.rmtree(self.directory)

    def _fanout(self, name):
        return (name[0:4], name[4:])

    def accept(self, item):
        if len(item) + self.sz > self.size:
            return False
        return True

    def put(self, item):
        self.check_type(item)
        if not self.accept(item):
            raise SSLFQueueCapacityError('refusing to accept item due to size')
        fanout,remainder = self._fanout(f'{int(time.time())}.{self.cn}')
        d = self._mkdir(fanout)
        fname = os.path.join(d, remainder)
        with open(fname, 'wb') as fh:
            log.debug('writing item to disk cache')
            fh.write(item)
        self.cn += 1
        self.sz += os.stat(fname).st_size

    def peek(self):
        for fname in self.files:
            with open(fname, 'rb') as fh:
                ret = fh.read()
                log.debug('peek() read %d bytes', len(ret))
                return ret

    def get(self):
        for fname in self.files:
            with open(fname, 'rb') as fh:
                ret = fh.read()
                log.debug('get() %d bytes', len(ret))
            self._counting_unlink(fname)
            return ret

    def getz(self, sz=SPLUNK_MAX_MSG):
        # Is it "dangerous" to unlink files during the os.walk (via generator)?
        # .oO( probably doesn't matter )
        r = b''
        for fname in self.files:
            with open(fname, 'rb') as fh:
                p = fh.read()
                log.debug('getz() %d bytes', len(p))
            if len(r) + len(self.sep) + len(p) > sz:
                break
            if r:
                r += self.sep
                log.debug(' ... %d bytes so far', len(p))
            r += p
            os._counting_unlink(fname)
        return r

    def pop(self):
        for fname in self.files:
            log.debug('pop()')
            self._counting_unlink(fname)
            break

    @property
    def files(self):
        def _k(x):
            try: return [ int(x) for x in x.split('.') ]
            except: pass
            return x
        for path, dirs, files in sorted(os.walk(self.directory)):
            for fname in [ os.path.join(path, f) for f in sorted(files, key=_k) ]:
                yield fname

    def _counting_unlink(self, fname, skip_unlink=False):
        sz = os.stat(fname).st_size
        if not skip_unlink:
            os.unlink(fname)
        self.cn -= 1
        self.sz -= sz

    def _count(self):
        log.debug('starting queue count')
        self.cn = 0
        self.sz = 0
        for fname in self.files:
            self.sz += os.stat(fname).st_size
            self.cn += 1
        log.debug('disk cache sizes: cn=%d sz=%d', self.cn, self.sz)

    @property
    def msz(self):
        return self.sz + max(0, self.cn-1)

    def __len__(self):
        return self.msz

class DiskBackedQueue:
    def __init__(self, directory, mem_size=DEFAULT_MEMORY_SIZE,
        disk_size=DEFAULT_DISK_SIZE, ok_types=OK_TYPES, fresh=False):

        self.dq = DiskQueue(directory, size=disk_size, ok_types=ok_types, fresh=fresh)
        self.mq = MemQueue(size=mem_size, ok_types=ok_types)

    def put(self, item):
        try:
            self.mq.put(item)
        except SSLFQueueCapacityError:
            self.dq.put(item)

    def peek(self):
        r = self.mq.peek()
        if r is None:
            r = self.dq.peek()
        return r

    def pop(self):
        if self.mq.cn:
            self.mq.pop()
        elif self.dq.cn:
            self.dq.pop()

    def unget(self, msg):
        self.mq.unget(msg)

    def _disk_to_mem(self):
        log.debug('populate memory queue with disk queue items')
        while self.dq.cn > 0:
            # NOTE: dq.peek() read()s the file but doesn't unlink()
            # dq.get() read()s the file and unlink()s it
            # dq.pop() just unlink()s the file
            # we attempt here to read each file exactly once — until the
            # stopping condition
            p = self.dq.peek()
            if self.mq.accept(p):
                self.mq.put(p)
                self.dq.pop()
                log.debug('mq.sz=%d dq.sz=%d', self.mq.sz, self.dq.sz)
            else:
                log.debug('memory queue is populated')
                break

    def get(self):
        r = self.mq.get()
        if r is None:
            r = self.dq.get()
        self._disk_to_mem()
        return r

    def getz(self, sz=SPLUNK_MAX_MSG):
        r = self.mq.getz(sz)
        if r is None:
            r = self.dq.getz(sz)
        elif len(r) < sz-1:
            r2 = self.dq.getz(sz-(len(r)+1))
            if r2:
                r += b' ' + r2
        self._disk_to_mem()
        return r

    @property
    def cn(self):
        return self.mq.cn + self.dq.cn

    @property
    def sz(self):
        return self.mq.sz + self.dq.sz
