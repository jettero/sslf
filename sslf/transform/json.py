import logging

log = logging.getLogger("sslf:trans:json")

import simplejson as json
from simplejson.errors import JSONDecodeError
from sslf.transform.rlep import ReLineEventProcessor

class JSONEventProcessor(ReLineEventProcessor):
    setup_json = ReLineEventProcessor.setup_rlep

    def json_post_process(self, item):
        return self.rlep_line(item)

    def grok_json(self, str_dat):
        str_dat = str_dat.strip()
        if not str_dat:
            return
        try:
            dat = json.loads(str_dat)
        except JSONDecodeError as e:
            if len(str_dat) > 80:
                str_dat = str_dat[0:79] + '…'
            log.warning('failed to decode "%s": %s', str_dat, e)
            return
        return self.json_post_process(dat)
