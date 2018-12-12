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
    _last_parsed_time = None

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
            self._last_parsed_time = evr['time'] = parsed_time
        elif self._last_parsed_time is not None:
            evr['time'] = self._last_parsed_time
            # NOTE: We try to persist the last parsed_time to deal with logs
            # like this, kinda hacky, but it seems to work.
            #
            #    2018-12-06 04:02:27,064 [salt.state       :1976][INFO    ][19345] Completed state
            #    2018-12-06 04:02:27,064 [salt.state       :1799][INFO    ][19345] Running state
            #    2018-12-06 04:02:27,064 [salt.state       :1832][INFO    ][19345] Executing state file.absent
            #    2018-12-06 04:02:27,071 [salt.state       :320 ][ERROR   ][19345] An exception occurred in this state:
            #      File "/python2.7/site-packages/salt/state.py", line 1913, in call
            #        **cdata['kwargs'])
            #      File "/python2.7/site-packages/salt/loader.py", line 1898, in wrapper
            #        return f(*args, **kwargs)
            #      File "/python2.7/site-packages/salt/states/file.py", line 1646, in absent
            #        __salt__['file.remove'](name)
            #      File "/python2.7/site-packages/salt/modules/file.py", line 3696, in remove
            #        'Could not remove \'{0}\': {1}'.format(path, exc)
        return evr
