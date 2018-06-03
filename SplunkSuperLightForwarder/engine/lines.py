import os
import shelve
from SplunkSuperLightForwarder.meta import MetaData

class Reader(MetaData):
    def __init__(self, path, meta_data_dir=None):
        self.path = path
        self.last_mtime = 0
        self.tell = 0
        self.mid = 'lines-reader-{}'.format(self.path.replace('/','_'))
        self.meta_data_dir = meta_data_dir

    @property
    def stat(self):
        if os.path.isfile(self.path):
            return os.stat(self.path)

    @property
    def ready(self):
        s = self.stat
        if s and s.st_size > 0 and s.st_mtime > self.last_mtime:
            return True
        return False

    def read(self):
        self.last_mtime = self.stat.st_mtime
        with open(self.path, 'r') as fh:
            fh.seek(self.tell)
            line = fh.readline()
            while line:
                yield line
                line = fh.readline()
            self.tell = fh.tell()
