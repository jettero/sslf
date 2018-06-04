import os
import shelve
from SplunkSuperLightForwarder.meta import MetaData

class Reader(MetaData):
    def __init__(self, path, meta_data_dir=None):
        self.path = path
        self.mtime = 0
        self.tell = 0
        self.mid = 'lines-reader-{}'.format(self.path.replace('/','_'))
        self.meta_data_dir = meta_data_dir
        self.load()

    def __repr__(self):
        return "lines.Reader({}[{}])".format(self.path, self.tell)

    def serialize(self):
        return {'path': self.path, 'mtime': self.mtime, 'tell': self.tell}

    def deserialize(self, dat):
        if self.path == dat.get('path'):
            self.mtime = dat.get('mtime', 0)
            self.tell = dat.get('tell', 0)

    @property
    def stat(self):
        if os.path.isfile(self.path):
            return os.stat(self.path)

    @property
    def ready(self):
        s = self.stat
        if s and s.st_size > 0 and s.st_mtime > self.mtime:
            return True
        return False

    def read(self):
        self.mtime = self.stat.st_mtime
        with open(self.path, 'r') as fh:
            fh.seek(self.tell)
            line = fh.readline()
            while line:
                yield line
                line = fh.readline()
            self.tell = fh.tell()
        self.save()
