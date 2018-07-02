# coding: UTF-8

import importlib
import argparse
import configparser
import os
import logging
import time
import signal
import daemonize
import collections

from SplunkSuperLightForwarder.hec import HEC
from SplunkSuperLightForwarder.util import AttrDict

def _dictify_args(args):
    if isinstance(args, argparse.Namespace):
        return args.__dict__
    elif isinstance(args, configparser.SectionProxy):
        return dict(args)
    return args

class Daemon(daemonize.Daemonize):
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
    logger = logging.getLogger('SSLF')

    log_level     = 'info'
    log_level_cli = 'debug'
    log_file      = '/var/log/sslf.log'
    log_fmt_cli   = '%(name)s [%(process)d] %(levelname)s: %(message)s'
    log_fmt       = '%(asctime)s ' + log_fmt_cli

    _path_config = dict()

    _fields = (
        'verbose', 'daemonize', 'config_file', 'meta_data_dir',
        'hec','token','index','sourcetype', 'pid_file',
        'log_level', 'log_level_cli', 'log_file', 'log_fmt_cli', 'log_fmt',
    )

    def __init__(self, *a, **kw):
        self._grok_args(kw, with_errors=True)

        # NOTE: this is kinda dumb, but makes sense in the right narative
        self.parse_args(a) # look for --config-file in cmdline args
        self.read_config() # read the config file, with possible --config-file override
        self.parse_args(a) # parse args again to make sure they override configs when given

        super(Daemon, self).__init__(app="SSLF", pid=self.pid_file, action=self.loop, logger=self.logger)

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
                raise Exception("{} is not a valid config argument".format(k))

    def add_path_config(self, path, args):
        if not path.startswith('/'):
            return
        self._path_config[path] = args

    def update_path_config(self):
        # NOTE: we want for the module lazy load to happen *after* we set up
        # daemon logging therefore, we store paths during config parse and
        # process them here in this later stage.
        # XXX: later, we should check to see if anything changed before tearing
        # everything down and rebuilding; perhaps during config re-parsing
        self.paths = dict()
        for p in self._path_config:
            self._grok_path(p, self._path_config[p])

    def _grok_path(self, path, args):
        if not path.startswith('/'):
            return
        pv = self.paths.get(path)
        if not pv:
            pv = self.paths[path] = AttrDict()
        pv.update(args)

        module = pv.pop('reader', 'lines')
        clazz  = pv.pop('class', 'Reader')
        if '.' not in module:
            module = 'SplunkSuperLightForwarder.reader.' + module

        try:
            m = importlib.import_module(module)
            c = getattr(m, clazz)
            o = c(path, meta_data_dir=self.meta_data_dir, config=pv)
            pv['reader'] = o
            self.logger.info("added %s to watchlist using %s", path, o)
        except ModuleNotFoundError as e:
            self.paths.pop(path, None)
            self.logger.error("couldn't find {1} in {0}: {2}".format(module,clazz,e))
            return

        hec_url = pv.get('hec', self.hec)
        token = pv.get('token', self.token)
        index = pv.get('index', self.index or 'tmp')
        sourcetype = pv.get('sourcetype', self.sourcetype or 'sslf:{}'.format(reader.__class__.__name__))
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
        config = configparser.ConfigParser()
        try:
            config.read(self.config_file)
        except Exception as e:
            self.logger.error("couldn't read config file {}: {}".format(self.config_file, e))
        for k in config:
            if k == 'sslf':
                self._grok_args(config[k])
            else:
                self.add_path_config(k, config[k])

    class HECEvent(AttrDict):
        def send(self):
            hec = self.pop('hec')
            event = self.pop('event')
            hec.send_event( event, **self )

    def step(self):
        for pv in self.paths.values():
            if pv.reader.ready:
                for evr in pv.reader.read():
                    yield self.HECEvent(hec=pv.hec, event=evr.event,
                        source=evr.source, time=evr.time, fields=evr.fields)

    def loop(self):
        self.update_path_config()
        while True:
            for ev in self.step():
                self.logger.debug("sending event (%s)", ev.hec)
                try:
                    ev.send()
                except Exception as e:
                    self.logger.error("error sending event (%s): %s", ev.hec, e)
            time.sleep(1)

    def numerical_log_level(self, x=None):
        if x is None:
            x = self.log_level
        h = logging.Handler()
        try:
            h.setLevel(int(x))
            return h.level
        except ValueError:
            try:
                # logging.DEBUG, debug, DEBUG, etc
                h.setLevel(x.upper().strip().split('.')[-1])
                return h.level
            except ValueError:
                raise ValueError(
                    "log_level='{}' is not understood (even with help) by python logging".format(self.log_level))
        # can we get here?? no?
        return logging.DEBUG

    def setup_logging(self, fmt=None, level=None, file=None):
        try:
            if self._logging_already_set_up is True:
                raise Exception("TODO: logging reconfigure")
        except: pass
        self._logging_already_set_up = True

        if self.daemonize or file is not None:
            fm = logging.Formatter(self.log_fmt if fmt is None else fmt, datefmt='%Y-%m-%d %H:%M:%S')
            fh = logging.FileHandler(self.log_file if file is None else file, 'a')
            fh.setFormatter(fm)
            fh.setLevel(self.numerical_log_level(self.log_level if level is None else level))
            self.logger.addHandler(fh)
            self.keep_fds = [ fh.stream.fileno() ]
        else:
            logging.basicConfig(
                level=self.numerical_log_level(
                    self.log_level_cli if level is None else level),
                format=self.log_fmt_cli if fmt is None else fmt)

    def kill_other(self):
        try:
            with open(self.pid_file, 'r') as fh:
                pid = int( fh.read().strip() )
            self.logger.warning('sending SIGTERM to other sslf pid=%d', pid)
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.1)
        except FileNotFoundError: pass
        except ValueError: pass

    def start(self):
        # Mostly people use logging.DEBUG and logging.INFO to setLevel() and
        # level=blah ... logging internally populates these constants with
        # numbers but internally also has a translator for going number->name
        # and name->number; it just has to be upper case.

        self.setup_logging()

        if self.daemonize:
            self.kill_other()
            self.logger.warning("becoming a daemon")
            super(Daemon, self).start()

        else:
            import sys
            signal.signal(signal.SIGINT, lambda sig,frame: sys.exit(0))
            self.loop()

def setup(*a, **kw):
    if len(a) == 1 and isinstance(a[0], (list,tuple,)):
        a = a[0]
    return Daemon(*a, **kw)

def run(*a, **kw):
    return setup(*a, **kw).start()
