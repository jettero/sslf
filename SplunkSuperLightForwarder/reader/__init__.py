
LOG_RLIMIT = 60
PROC_RESTART_RLIMIT = 60

import logging

log = logging.getLogger("sslf:reader")

from SplunkSuperLightForwarder.re   import ReEngine
from SplunkSuperLightForwarder.util import AttrDict, DateParser

class ReLineEventProcessor(object):

    def setup_rlep(self, config=None):
        self.parse_time = config.get('parse_time')

        patterns = dict()
        if config is not None:
            for k in config:
                if k.startswith('re_'):
                    patterns[ k[3:] ] = config[k]

        self._re = ReEngine(**patterns)

    def rlep_line(self, line):
        evr = AttrDict(event=line, source=self.path, fields=self._re(line))
        ptv = evr.fields.get(self.parse_time)
        if ptv:
            log.debug("parsing field=%s value=%s as a datetime", self.parse_time, ptv)
            dp = DateParser(ptv)
            evr['time'] = dp.tstamp
            log.debug(" parsed time is %s", dp.fmt)
        return evr
