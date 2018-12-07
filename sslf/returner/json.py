# coding: utf-8

import logging
from . hec import HEC, SendEventResult

log = logging.getLogger('sslf:returner:json')

# XXX: all returners are presumed to be HEC objects this is kinda dumb, but
# since the only non-HEC returner we have so far is a json dumper for testing
# purposes ... it's maybe fine for now.

class JSONReturner(HEC):
    encode_event = HEC.encode_event

    def __init__(self, *a, **kw):
        super(JSONReturner, self).__init__(*a, **kw)
        self.file = self.url
        if self.file.startswith('file://'):
            self.file = self.file[7:]
        if not self.file.startswith('/'):
            self.file = '/tmp/' + self.file

    def _send_event(self, encoded_payload):
        with open(self.file, 'ab') as fh:
            fh.write(encoded_payload)
            fh.write(b'\n')
        return SendEventResult.data_ok({})


Returner = JSONReturner
