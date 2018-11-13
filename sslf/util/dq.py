import os
import logging
import time
import shutil
from collections import deque

log = logging.getLogger(__name__)

OK_TYPES = (bytes,bytearray,)
SPLUNK_MAX_MSG = 100000
DEFAULT_MEMORY_SIZE = SPLUNK_MAX_MSG * 5
DEFAULT_DISK_SIZE = DEFAULT_MEMORY_SIZE * 1000

class SSLFQueueTypeError(Exception):
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

    def __init__(self, max_msz=DEFAULT_MEMORY_SIZE, ok_types=OK_TYPES):
        self.init_types(ok_types)
        self.init_mq(max_msz)

    def init_mq(self, max_msz):
        self.max_msz = max_msz
        # compose rather than inherit to limit operations to append()/popleft() and
        # ignore the rest of the deque() functionality
        self.mq = deque()

    def put(self, item):
        self.check_type(item)
        # XXX: so what do we do if we're past the max_msz?
        # 1. toss the new item?
        # 2. toss an old item?
        # 3. block until there's room?
        self.mq.append(item)

    def get(self):
        if len(self.mq) > 0:
            return self.mq.popleft()

    def getz(self, sz=SPLUNK_MAX_MSG):
        r = b''
        while len(self.mq) > 0 and len(r) + len(self.sep) + len(self.peek()) < sz:
            if r:
                r += self.sep
            r += self.mq.popleft()
        return r

    def peek(self):
        if len(self.mq) > 0:
            return self.mq[0]

    @property
    def msz(self):
        s = 0
        for i in self.mq:
            s += len(i)
        return s

    @property
    def msgsz(self):
        return self.msz + max(0, len(self.sep) * (len(self.mq) -1))

    def __len__(self):
        return self.msgsz


class DiskQueue(OKTypesMixin):
    sep = b' '

    def __init__(self, directory, max_dsz=DEFAULT_DISK_SIZE, ok_types=OK_TYPES, fresh=False):
        self.init_types(ok_types)
        self.init_dq(directory, max_dsz)
        if fresh:
            self.clear()
        self._count()

    def init_dq(self, directory, max_dsz):
        self.directory = directory
        self.max_dsz = max_dsz

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

    def put(self, item):
        self.check_type(item)
        fanout,remainder = self._fanout(f'{int(time.time())}.{self.dcn}')
        d = self._mkdir(fanout)
        f = os.path.join(d, remainder)
        with open(f, 'wb') as fh:
            fh.write(item)
        self._count()

    def peek(self):
        for fname in self.files:
            with open(fname, 'rb') as fh:
                return fh.read()

    def get(self):
        for fname in self.files:
            with open(fname, 'rb') as fh:
                ret = fh.read()
            os.unlink(fname)
            self._count()
            return ret

    def getz(self, sz=SPLUNK_MAX_MSG):
        # Is it "dangerous" to unlink files during the os.walk (via generator)?
        # .oO( probably doesn't matter )
        r = b''
        for fname in self.files:
            with open(fname, 'rb') as fh:
                p = fh.read()
            if len(r) + len(self.sep) + len(p) > sz:
                break
            if r:
                r += self.sep
            r += p
            os.unlink(fname)
        self._count()
        return r

    @property
    def files(self):
        for path, dirs, files in sorted(os.walk(self.directory)):
            for fname in [ os.path.join(path, f) for f in sorted(files) ]:
                yield fname

    def _count(self):
        self.dcn = 0
        self.dsz = 0
        for fname in self.files:
            self.dsz += os.stat(fname).st_size
            self.dcn += 1

    @property
    def msgsz(self):
        return self.dsz + max(0, self.dcn-1)

    def __len__(self):
        return self.msgsz
