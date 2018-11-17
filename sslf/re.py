
import re
import logging
from collections import namedtuple

REGEX_FIELDS = re.compile(r'^(?P<regex_name>[^:+]+?)(?::(?P<input>.+?))?(?:\+(?P<flags>.+))?$')
REItem = namedtuple('REItem', ['re', 'field', 'flags'])

class ReEngine:
    def __init__(self, **re_config):
        self.logger = logging.getLogger('sslf:re')
        self.set_re(**re_config)

    def set_re(self, **re_config):
        self._re = dict()
        self.add_re(**re_config)

    def add_re(self, **re_config):
        for rk in re_config:
            m = REGEX_FIELDS.match(rk)
            if m:
                rname, infield, flags = m.groups()
            else:
                rname, infield, flags = rk,None,None
            if rname.startswith('re_') and rname != 're_':
                rname = rname[3:]

            try:
                self._re[rname] = REItem(re=re.compile(re_config[rk]), field=infield, flags=flags)
            except Exception as e:
                self.logger.error('error compiling regular expression (%s: %s): %s',
                    rname, re_config[rk], e)

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

        searchable = input if isinstance(input,dict) else dict()
        fields = dict()

        for rname,ri in self._re.items():
            ii = searchable.get(ri.field, input) if ri.field else input
            if isinstance(ii, dict):
                ii = tuple(ii.values())
            if not isinstance(ii, (list,tuple)):
                ii = (ii,)

            for i in ii:
                if isinstance(i, (str,bytes,bytearray)):
                    m = ri.re.search(i)
                    if m:
                        gd = m.groupdict()
                        if gd:
                            fields.update(gd)
                            searchable.update(gd)
                        else:
                            for k,v in enumerate(m.groups()):
                                fields[k+1] = v
                                searchable[k+1] = v
        return fields

    def __call__(self, input):
        return self.compute_fields(input)

    def __bool__(self):
        if self._re:
            return True
        return False
