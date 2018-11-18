import re
import logging

log = logging.getLogger("sslf:trans:rlep")

from sslf.re   import ReEngine
from sslf.util import AttrDict, DateParser

# date +\%s.\%N
# 1542551942.943691901
# 1542551942.943691901
parse_ts_re = re.compile(r'\s*(?P<ts>\d{7,10})(?P<ns>\d*)\s*')

class ReLineEventProcessor:

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
        parsed_time = None
        if ptv:
            m = parse_ts_re.match(ptv)
            if m:
                gd = m.groupdict()
                log.debug('understood %s to be a timestamp: %s', ptv, gd)
                parsed_time = gd['ts']
                if gd['ns']:
                    parsed_time += '.' + gd['ns']
            else:
                log.debug("parsing field=%s value=%s as a datetime", self.parse_time, ptv)
                dp = DateParser(ptv)
                parsed_time = dp.tstamp
                log.debug(" parsed time is %s", dp.fmt)
        if parsed_time:
            log.debug('setting evr.time = %s', parsed_time)
            evr['time'] = parsed_time
        return evr
