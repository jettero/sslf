# coding: UTF-8

import importlib
import argparse
import configparser
import os, sys
import logging
import time
import signal
import daemonize
import collections

from sslf.returner import HEC
from sslf.util import AttrDict, RateLimit, build_tzinfos

log = logging.getLogger("sslf")

def _dictify_args(args):
    if isinstance(args, argparse.Namespace):
        return args.__dict__
    elif isinstance(args, configparser.SectionProxy):
        return dict(args)
    return args

class DaemonConfig(Exception):
    pass

class LoggingConfig(Exception):
    pass

class Daemon(daemonize.Daemonize):
    filter_logs = False
    pid_file = '/var/run/sslf.pid'
    verbose = False
    daemonize = False
    config_file = '/etc/sslf.conf'
    meta_data_dir = '/var/cache/sslf'
    paths = None
    hec = None
    token = None
    index = None
    sourcetype = None
    logger = log
    tz_load_re = '^(GMT|UTC)|^(US|Europe|Asia)/'

    log_level     = 'info'
    log_file      = '/var/log/sslf.log'
    log_fmt_cli   = '%(name)s [%(process)d] %(levelname)s: %(message)s'
    log_fmt       = '%(asctime)s ' + log_fmt_cli

    _path_config = dict()

    _fields = (
        'verbose', 'daemonize', 'config_file', 'meta_data_dir',
        'hec','token','index','sourcetype', 'pid_file',
        'log_level', 'log_file', 'log_fmt_cli', 'log_fmt',
        'tz_load_re',
    )

    def __init__(self, *a, **kw):
        try:
            self._grok_args(kw, with_errors=True)

            # NOTE: this is kinda dumb, but makes sense in the right narative
            self.parse_args(a) # look for --config-file in cmdline args
            self.read_config() # read the config file, with possible --config-file override
            self.parse_args(a) # parse args again to make sure they override configs when given
        except Exception as e:
            raise DaemonConfig(f'daemon configuration failure: {e}') from e

        try:
            self.setup_logging()
        except Exception as e:
            raise LoggingConfig(f'logging configuration failed: {e}') from e

        import sre_constants
        try:
            build_tzinfos(self.tz_load_re)
        except sre_constants.error as e:
            raise DaemonConfig(f'error parsing tz_load_re="{self.tz_load_re}": {e}') from e

        self.update_path_config() # no need to trap this one, it should go to logging

        super(Daemon, self).__init__(app="SSLF", pid=self.pid_file,
            action=self.loop,
            keep_fds=self.keep_fds, # have to pass this in or self.keep_fds=None, meh
            logger=log # same
        )

    def _barf_settings(self):
        ret = dict()
        method_type = type(self._barf_settings)
        for k in dir(self):
            if not k.startswith('_'):
                a = getattr(self, k)
                if not isinstance(a, method_type):
                    ret[k] = a
        return ret

    def _grok_args(self, args, with_errors=False):
        args = _dictify_args(args)
        for k in args:
            if k in self._fields:
                if isinstance(args[k], (str,)):
                    if args[k].lower() in ('false', 'no', '0',): args[k] = False
                    elif args[k].lower() in ('true', 'yes', '1',): args[k] = True
                setattr(self,k, args[k])
            elif with_errors:
                raise Exception(f'{k} is not a valid config argument')

    def add_path_config(self, path, args):
        if not path.startswith('/'):
            return
        if path not in self._path_config:
            self._path_config[path] = dict()
        self._path_config[path].update(args)

    def update_path_config(self):
        # NOTE: we want for the module lazy load to happen *after* we set up
        # daemon logging therefore, we store paths during config parse and
        # process them here in this later stage.
        # XXX: later, we should check to see if anything changed before tearing
        # everything down and rebuilding; perhaps during config re-parsing
        self.paths = dict()
        for p in self._path_config:
            self._grok_path(p, self._path_config[p])
        return self

    def _grok_path(self, path, args):
        log.debug(f'trying to figure out config path={path}')
        if not path.startswith('/'):
            return
        pv = self.paths.get(path)
        if not pv:
            pv = self.paths[path] = AttrDict()
        pv.update(args)

        if not pv.get('meta_data_dir'):
            pv['meta_data_dir'] = self.meta_data_dir

        module = pv.pop('reader', 'lines')
        clazz  = pv.pop('class', 'Reader')
        if '.' not in module:
            module = 'sslf.reader.' + module

        try:
            m = importlib.import_module(module)
            c = getattr(m, clazz)
            o = c(path, config=pv)
            pv['reader'] = o
            log.info("added %s to watchlist using %s", path, o)
        except ModuleNotFoundError as e:
            self.paths.pop(path, None)
            log.error(f"couldn't find {module} in {clazz}: {e}")
            return

        hec_url = pv.get('hec', self.hec)
        token = pv.get('token', self.token)
        index = pv.get('index', self.index or 'tmp')

        if not hec_url or not token or not index:
            log.warn("couldn't figure out hec settings for path=%s, skipping", path)
            return

        sourcetype = pv.get('sourcetype', self.sourcetype)
        if not sourcetype:
            try:
                sourcetype = pv['reader'].default_sourcetype
            except:
                sourcetype = 'sslf:' + module.split('.')[-1]

        pv['hec'] = HEC(
            hec_url, token, sourcetype=sourcetype, index=index,
            # TODO: surely some people will want to verify this, add option,
            # default to true
            verify_ssl=False
        )


    def parse_args(self, a):
        parser = argparse.ArgumentParser(description="this is program") # options and program name are automatic
        parser.add_argument('-v', '--verbose', action='store_true')
        parser.add_argument('-f', '--daemonize', action='store_true', help="fork and become a daemon")
        parser.add_argument('-l', '--log-level', type=str, default=self.log_level,
            help="daemon logging level (default: %(default)s)")
        parser.add_argument('-c', '--config-file', type=str, default=self.config_file,
            help="config file (default: %(default)s)")
        parser.add_argument('-m', '--meta-data-dir', type=str, default=self.meta_data_dir,
            help="location of meta data (default: %(default)s)")
        args = parser.parse_args(a) if a else parser.parse_args()
        self._grok_args(args)

    def read_config(self):
        if not self.config_file:
            return
        config = configparser.ConfigParser()
        try:
            log.debug("parsing config_file=%s", self.config_file)
            config.read(self.config_file)
        except Exception as e:
            log.error(f"couldn't read config file {self.config_file}: {e}")
        for k in config:
            if k == 'sslf':
                self._grok_args(config[k])
            else:
                self.add_path_config(k, config[k])

    def step(self):
        for pv in self.paths.values():
            if pv.reader.ready:
                log.debug("%s says its ready, reading", pv.reader)
                for evr in pv.reader.read():
                    log.debug("received event from %s, sending to hec %s", pv.reader, pv.hec)
                    try:
                        pv.hec.send_event(evr)
                    except Exception as e:
                        log.error("error sending event to %s: %s", pv.hec, e)

    def loop(self):
        while True:
            self.step()
            time.sleep(1)

    @property
    def log_level_n(self):
        # Mostly people use logging.DEBUG and logging.INFO to setLevel() and
        # level=blah ... logging internally populates these constants with
        # numbers but internally also has a translator for going number->name
        # and name->number; it just has to be upper case.

        h = logging.Handler()
        try:
            h.setLevel(int(self.log_level))
            return h.level
        except ValueError:
            try:
                # logging.DEBUG, debug, DEBUG, etc
                h.setLevel(self.log_level.upper().strip().split('.')[-1])
                return h.level
            except ValueError:
                raise ValueError( f"log_level='{self.log_level}'"
                    " is not understood (even with help) by python logging")
        # can we get here?? no?
        return logging.DEBUG

    def setup_logging(self, fmt=None, level=None, file=None):
        try:
            if self._logging_already_set_up is True:
                raise Exception("TODO: logging reconfigure")
        except: pass
        self._logging_already_set_up = True

        bc_kw = {
            'datefmt': '%Y-%m-%d %H:%M:%S',
            'format': self.log_fmt if fmt is None else fmt,
            'level': self.log_level_n,
        }

        if self.daemonize or file is not None:
            bc_kw['filename'] = self.log_file if file is None else file

        logging.basicConfig( **bc_kw )
        self.keep_fds = [ h.stream.fileno() for h in logging.root.handlers
            if isinstance(h, logging.FileHandler) ]

        if self.filter_logs:
            fl = lambda r: 'sslf' in r.pathname or 'SSLF' in r.name
            for h in logging.root.handlers:
                h.addFilter(fl)

        log.info('logging configured')

        return self

    def kill_other(self):
        try:
            with open(self.pid_file, 'r') as fh:
                pid = int( fh.read().strip() )
            log.warn('sending SIGTERM to other sslf pid=%d', pid)
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.1)
        except FileNotFoundError: pass
        except ValueError: pass

    def start(self):
        if self.daemonize:
            self.kill_other()
            super(Daemon, self).start()

        else:
            import sys
            signal.signal(signal.SIGINT, lambda sig,frame: sys.exit(0))
            self.loop()

def setup(*a, **kw):
    if len(a) == 1 and isinstance(a[0], (list,tuple,)):
        a = a[0]
    try:
        return Daemon(*a, **kw)
    except Exception as e:
        if isinstance(e, (DaemonConfig, LoggingConfig)):
            print("fatal error in daemon setup:", e)
            sys.exit(1)
        raise

def run(*a, **kw):
    return setup(*a, **kw).start()