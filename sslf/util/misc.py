import time, os, re
import dateutil.parser, dateutil.tz

__all__ = ['AttrDict', 'RateLimit', 'LogLimit', 'build_tzinfos']

class AttrDict(dict):
    def __getattribute__(self, name):
        try: return super(AttrDict, self).__getattribute__(name)
        except: pass
        return self.get(name)

DEFAULT_RATE_LIMIT = 1
class RateLimit:
    limits = dict()

    def __init__(self, tag, limit=DEFAULT_RATE_LIMIT):
        self.tag = tag
        self.limit = limit

    @property
    def dt(self):
        return time.time() - self.limits.get(self.tag, 0)

    @property
    def dt_ok(self):
        return self.dt >= self.limit

    def __bool__(self):
        return self.dt_ok

    def __enter__(self):
        return self

    def __exit__(self, e_type=None, e_val=None, e_tb=None):
        if self.dt_ok and not (e_type or e_val or e_tb):
            # only increment the tag time iff dt is ok and
            # there's no exception bringing us here
            self.limits[self.tag] = time.time()
        # returning nothing tells with() to re-raise whatever exception was received

    def __repr__(self):
        return f'{self.__class__.__name__}( tag={self.tag}, dt={self.dt}, ok={self.dt_ok} )'

class LogLimit(RateLimit):
    def __init__(self, logger, *a, limit=DEFAULT_RATE_LIMIT):
        self.logger = logger
        self.format = a[0]
        super(LogLimit, self).__init__('|'.join(a), limit=limit)

    def debug(self, *a, **kw):
        if self.dt_ok:
            self.logger.debug(self.format, *a, **kw)

    def info(self, *a, **kw):
        if self.dt_ok:
            self.logger.info(self.format, *a, **kw)

    def error(self, *a, **kw):
        if self.dt_ok:
            self.logger.error(self.format, *a, **kw)

tzinfos = dict()
def build_tzinfos(load_re='^...$|^US/'):
    r = re.compile(load_re.strip())

    from . import _common_tz
    for i in _common_tz.common_timezones:
        # NOTE: this probably isn't super reliable for various reasons:
        # 1) these abbreviations are notoriously ambiguous
        # 2) I'm using tzinfo._trans_idx (clearly meant to be a secret)
        # 3) why do I only look at the last 10 transitions? why not the last 30?
        # 4) ... or the last 2? seems kinda arbitrary, neh?
        # ?) other things I'm not thinking of
        # It does have the benefit of being rather simple though.
        if r.search(i):
            tzinfo = dateutil.tz.gettz(i)
            tranil = dict([ (x.abbr,tzinfo) for x in tzinfo._trans_idx[-10:] ])
            tzinfos.update(tranil)

class DateParser:
    def __init__(self, date_string, fmt='%Y-%m-%d %H:%M:%S %Z/%z', guess_tz=os.environ.get('TZ','UTC')):
        self.orig   = date_string
        self.parsed = dateutil.parser.parse(date_string, tzinfos=tzinfos)
        if self.parsed.tzinfo is None:
            self.parsed = self.parsed.replace(tzinfo=dateutil.tz.gettz())
        self.tstamp = time.mktime(self.parsed.timetuple())
        self.fmt    = self.parsed.strftime(fmt)

    def __repr__(self):
        return f'DateParsed({self.orig} -> {self.fmt})'
    __str__ = __repr__
