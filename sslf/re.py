
import re
import logging

FIELD_NAME_FORMAT = re.compile(r'^(?P<field_name>[^:+]+?)(?::(?P<input>.+?))?(?:\+(?P<flags>.+))?$')

class ReEngine:
    def __init__(self, **re_config):
        self.logger = logging.getLogger('sslf:re')
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
        ''' take a string argument `input` and apply patterns to it
            patterns of the form `name:keyname` will attempt to search in
            keyname of the return dictionary instead of the given input.

                from sslf.re import ReEngine
                RE = ReEngine(**{'b1': r'(?P<k1>this\s+is)\s+(?P<blah>.+?)\s*$',
                    'b2:blah': r'^my\s+(?P<k2>\S+)'})
                res = RE.compute_fields('this is my thingy')

            gives a `res` like this

                {'k1': 'this', 'blah': 'is my thingy', 'k2': 'thingy'}


            If the given `input` is a `dict`, then we assume some form of
            preparsing has already been performed at set the return dictionary
            to input, then proceed to parse (probably only succeeding on
            patterns with key specifiers.

                res2 = RE.compute_fields({'blah': 'my whatever'})

            gives a `res2` like this

                {'blah': 'my whatever', 'k2': 'whatever'}
        '''

        ret = input if isinstance(input,dict) else dict()

        for rk in self._re:
            m = FIELD_NAME_FORMAT.match(rk)
            if m:
                _, _input, _flags = m.groups()
            else:
                _, _input, _flags = rk, None, None

            ii = ret.get(_input, input) if _input else input
            if isinstance(ii, dict):
                ii = tuple(ii.values())
            if not isinstance(ii, (list,tuple)):
                ii = (ii,)

            for i in ii:
                if isinstance(i, (str,bytes,bytearray)):
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
