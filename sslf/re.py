
import re
import logging
import copy
from collections import namedtuple, deque

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
            preparsing has already been performed and attempt to apply only
            field searches to the input

                res2 = RE.compute_fields({'blah': 'my whatever'})

            gives a `res2` like this

                {'blah': 'my whatever', 'k2': 'whatever'}
        '''

        searchable = copy.deepcopy(input) if isinstance(input, dict) else dict()
        fields = dict()

        todo = deque( self._re.items() )
        fields_to_find = True
        while fields_to_find and todo:
            fields_to_find = False
            rname,ri = todo.popleft()
            if ri.field:
                if ri.field not in searchable:
                    todo.append( (rname,ri) )
                    self.logger.debug('skipping (for now) %s="%s", "%s" not found in searchable fields',
                        rname,ri.re.pattern, ri.field)
                    continue
                else:
                    ii = searchable[ri.field]
                    self.logger.debug('applying %s="%s" to "%s"', rname,ri.re.pattern, ri.field)
            else:
                ii = input
                self.logger.debug('applying %s="%s"', rname,ri.re.pattern)

            if not isinstance(ii, str):
                self.logger.debug('refusing to process nonstring data')
                continue

            m = ri.re.search(ii)
            if m:
                # if we populate fields in searchable, we need to go around
                # again in case there's subsearches in that field
                fields_to_find = True
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
