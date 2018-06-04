import os, posix
import shelve
import hashlib
import logging
from SplunkSuperLightForwarder.meta import MetaData

log = logging.getLogger('linesReader')

class Sig(object):
    def __init__(self, h='', b=0):
        self.h = h
        self.b = b

    def __repr__(self):
        return "Sig({0.h}[{0.b}])".format(self)
    __str__ = __repr__

    def __eq__(self, other):
        if isinstance(other, Sig):
            return self.h == other.h and self.b == other.b
        return self.h == other # assume we're looking at a string

    def __ne__(self, other):
        return not( self == other )

    def serialize(self):
        return (self.h, self.b)

class Reader(MetaData):
    def __init__(self, path, meta_data_dir=None, signature_bytes=1024):
        self._reset()
        self.sbytes = signature_bytes
        self.path = path
        self.mid = 'lines-reader-{}'.format(self.path.replace('/','_'))
        self.meta_data_dir = meta_data_dir
        self.load()
        self.trunc_check()

    def __repr__(self):
        return "lines.Reader({}[{}])".format(self.path, self.tell)

    def _reset(self):
        self.mtime = self.tell = self.size = 0
        self._save_sig(0)

    def gen_sig(self, limit=None):
        if limit is True:       sb = self.sig.b
        elif limit is not None: sb = limit
        else:                   sb = self.sbytes

        if sb > 0:
            with open(self.path, 'r') as fh:
                b = fh.read(sb)

        else: b = ''

        h = hashlib.md5(b.encode()).hexdigest()
        return Sig(h, len(b))

    def _save_sig(self, limit=None):
        self.sig = self.gen_sig(limit)

    def trunc_check(self):
        st = self.stat
        log.debug("here1")
        if st.st_mtime > self.mtime and st.st_size < self.size:
            log.debug("here1.5")
            self._reset()
            return False
        log.debug("here2 gen_sig=%s, self_sig=%s",
            self.gen_sig(True), self.sig)
        if self.gen_sig(True) != self.sig:
            log.debug("here2.5")
            self._reset()
            return False
        log.debug("here3")
        return True

    def serialize(self):
        return {'path': self.path, 'mtime': self.mtime, 'tell': self.tell,
            'size': self.size, 'sig': self.sig.serialize() }

    def deserialize(self, dat):
        if self.path == dat.get('path'):
            for k in ('mtime','tell','size','sig',):
                setattr(self, k, dat.get(k, 0))
            if self.sig == 0:
                self._save_sig(0)
            else:
                self.sig = Sig( *self.sig )

    @property
    def stat(self):
        if os.path.isfile(self.path):
            return os.stat(self.path)
        return posix.stat_result( (0,)*10 )

    def _save_stat(self, tell=None):
        st = self.stat
        self.mtime = st.st_mtime
        self.size  = st.st_size
        if tell is not None:
            self.tell = tell
        if st.st_size > self.sig.b and self.sig.b < self.sbytes:
            self._save_sig()

    @property
    def ready(self):
        self.trunc_check()
        s = self.stat
        if s.st_size > 0 and s.st_mtime > self.mtime:
            return True
        return False

    def read(self):
        with open(self.path, 'r') as fh:
            fh.seek(self.tell)
            line = fh.readline()
            while line:
                yield line
                line = fh.readline()
            self._save_stat( fh.tell() )
        self.save()
