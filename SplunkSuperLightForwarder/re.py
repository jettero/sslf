
import re
import logging

FIELD_NAME_FORMAT = re.compile(r'^(?P<field_name>[^:+]+?)(?::(?P<input>.+?))?(?:\+(?P<flags>.+))?$')

class ReEngine(object):
    def __init__(self, **re_config):
        self.logger = logging.getLogger('ReEngine')
        self.set_re(**re_config)

    def set_re(self, **re_config):
        self._re = dict()
        self.add_re(**re_config)

    def add_re(self, **re_config):
        for rk in re_config:
            if rk not in self._re:
                self._re[rk] = list()
            try:
                self._re[rk].append( re.compile(re_config[rk]) )
            except Exception as e:
                self.logger.error('error compiling regular expression (%s: %s): %s',
                    rk, re_config[rk], e)

    def compute_fields(self, input):
        ret = dict()
        for rk in self._re:
            m = FIELD_NAME_FORMAT.match(rk)
            if m:
                _, _input, _flags = m.groups()
            else:
                _, _input, _flags = rk, None, None
            i = ret.get(_input, input) if _input else input
            for r in self._re[rk]:
                m = r.search(i)
                if m:
                    gd = m.groupdict()
                    if gd:
                        ret.update(gd)
                    else:
                        for k,v in enumerate(m.groups()):
                            ret[k+1] = v
        return ret

    def __call__(self, input):
        return self.compute_fields(input)

    def __bool__(self):
        if self._re:
            return True
        return False
