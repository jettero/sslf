import os

class Reader(object):
    def __init__(self, path):
        self.path = path
        self.last_mtime = 0
        self.tell = 0

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
