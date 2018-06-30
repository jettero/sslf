import time

class AttrDict(dict):
    def __getattribute__(self, name):
        try: return super(AttrDict, self).__getattribute__(name)
        except: pass
        return self.get(name)

class RateLimit(object):
    limits = dict()

    def __init__(self, tag, limit=300):
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

    def __exit__(self, e_type, e_val, e_tb):
        if self.dt_ok:
            self.limits[self.tag] = time.time()
        # returning nothing tells with() to re-raise whatever exception was received

    def __repr__(self):
        return "{}( tag={}, dt={}, ok={} )".format( self.__class__.__name__,
            self.tag, self.dt, self.dt_ok )

class LogLimit(RateLimit):
    def __init__(self, logger, *a, limit=300):
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
