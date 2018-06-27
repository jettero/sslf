import os, posix
import shelve
import hashlib
import logging
import dateutil.parser
import time
from SplunkSuperLightForwarder.meta import MetaData
from SplunkSuperLightForwarder.re   import ReEngine
from SplunkSuperLightForwarder.util import AttrDict

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
    def __init__(self, path, meta_data_dir=None, signature_bytes=1024, config=None):
        self._reset()
        self.sbytes = signature_bytes
        self.path = path
        self.mid = 'lines-reader-{}'.format(self.path.replace('/','_'))
        self.meta_data_dir = meta_data_dir
        self.load()
        self.trunc_check()

        self.parse_time = config.get('parse_time')

        patterns = dict()
        if config is not None:
            for k in config:
                if k.startswith('re_'):
                    patterns[ k[3:] ] = config[k]
        self._re = ReEngine(**patterns)

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
            try:
                with open(self.path, 'r') as fh:
                    b = fh.read(sb)
            except IOError as e:
                log.debug("gen_sig(%s): %s", self.path, e)
                self._reset()
                b = ''

        else: b = ''

        h = hashlib.md5(b.encode()).hexdigest()
        return Sig(h, len(b))

    def _save_sig(self, limit=None):
        self.sig = self.gen_sig(limit)

    def trunc_check(self):
        st = self.stat
        if st.st_mtime > self.mtime and st.st_size < self.size:
            self._reset()
            return False
        if self.gen_sig(True) != self.sig:
            self._reset()
            return False
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
        try:
            return os.stat(self.path)
        except IOError as e:
            log.debug("stat(%s): %s", self.path,e)
            self._reset()
        return posix.stat_result( (0,)*10 )

    def _save_stat(self, tell=None):
        st = self.stat
        self.mtime = st.st_mtime
        self.size  = st.st_size
        self.tell = 0 if tell is None else tell
        if st.st_size > self.sig.b and self.sig.b < self.sbytes:
            self._save_sig()

    @property
    def ready(self):
        self.trunc_check()
        s = self.stat
        if s.st_size > 0 and s.st_size > self.size and s.st_mtime >= self.mtime:
            return True
        return False

    def read(self):
        try:
            with open(self.path, 'r') as fh:
                fh.seek(self.tell)
                while True:
                    line = fh.readline()
                    if not line:
                        break
                    evr = AttrDict(event=line, source=self.path, fields=self._re(line))
                    ptv = evr.fields.get(self.parse_time)
                    if ptv:
                        log.debug("parsing field=%s value=%s as a datetime", self.parse_time, ptv)
                        parsed = dateutil.parser.parse(ptv)
                        evr['time'] = time.mktime( parsed.timetuple() )
                        log.debug(" parsed time is %s", evr['time'])
                    yield evr
                    self._save_stat( fh.tell() )
        except IOError as e:
            log.error("read(%s): %s", self.path, e)
        self.save()
