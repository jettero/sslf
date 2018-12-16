
import logging

from sslf.reader.lines import Reader as LinesReader
from sslf.transform.json import JSONEventProcessor

log = logging.getLogger(__name__)

class Reader(LinesReader, JSONEventProcessor):

    def read(self):
        for item in super(Reader, self).read():
            l = self.grok_json(item['event'])
            if l:
                yield l
            else:
                log.debug("unable to grok_json(%s)", item)
