
from sslf.reader.cmdlines import Reader as CommandLinesReader
from sslf.transform.json import JSONEventProcessor

class Reader(CommandLinesReader, JSONEventProcessor):
    def read(self):
        l = True
        while self.spoll and l:
            l = self._proc.stdout.readline()
            if l:
                l = self.grok_json(l.decode('utf-8', 'ignore'))
                if l:
                    yield l
            elif self.died:
                self.wait()
