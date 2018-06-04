# coding: UTF-8

import importlib
import argparse
import configparser
import os
import logging
import time

from SplunkSuperLightForwarder.hec import HEC

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('SSLF')

def _dictify_args(args):
    if isinstance(args, argparse.Namespace):
        return args.__dict__
    elif isinstance(args, configparser.SectionProxy):
        return dict(args)
    return args

class Daemon(object):
    verbose = False
    daemonize = False
    config_file = '/etc/sslf.conf'
    meta_data_dir = '/var/cache/sslf'
    paths = None
    hec = None
    token = None
    index = None
    sourcetype = None

    _fields = (
        'verbose', 'daemonize', 'config_file', 'meta_data_dir',
        'hec','token','index','sourcetype',
    )

    def __init__(self, *a, **kw):
        self._grok_args(kw, with_errors=True)
        self.parse_args(a)
        self.read_config()

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
                setattr(self,k, args[k])
            elif with_errors:
                raise Exception("{} is not a valid config argument".format(k))

    def _grok_path(self, path, args):
        if not path.startswith('/'):
            return
        if self.paths is None:
            self.paths = dict()
        if path not in self.paths:
            self.paths[path] = dict()
        self.paths[path].update(args)
        engine = self.paths.pop('engine', 'lines')
        clazz  = self.paths.pop('class', 'Reader')
        if '.' not in engine:
            engine = 'SplunkSuperLightForwarder.engine.' + engine
        try:
            m = importlib.import_module(engine)
            c = getattr(m, clazz)
            self.paths[path]['reader'] = c(path, meta_data_dir=self.meta_data_dir)
            log.info("added %s to watchlist using %s", path, self.paths[path]['reader'])
        except ModuleNotFoundError as e:
            self.paths.pop(path, None)
            log.error("couldn't find {1} in {0}: {2}".format(engine,clazz,e))

    def parse_args(self, a):
        parser = argparse.ArgumentParser(description="this is program") # options and program name are automatic
        parser.add_argument('-v', '--verbose', action='store_true')
        parser.add_argument('-n', '--no-daemonize', action='store_true',
            help="don't fork and become a daemon")
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
            log.error("couldn't read config file {}: {}".format(self.config_file, e))
        for k in config:
            if k == 'sslf':
                self._grok_args(config[k])
            else:
                self._grok_path(k, config[k])

    def start(self):
        while True:
            for pv in self.paths.values():
                reader = pv['reader']
                hec_url = pv.get('hec', self.hec)
                token = pv.get('token', self.token)
                index = pv.get('index', self.index or 'tmp')
                sourcetype = pv.get('sourcetype', self.sourcetype or 'sslf:{}'.format(reader.__class__.__name__))
                hec = HEC(hec_url, token, sourcetype=sourcetype, index=index, verify_ssl=False)
                if reader.ready:
                    for item in reader.read():
                        log.info("sending event (hec=%s, index=%s, sourcetype=%s)",
                            hec_url, index, sourcetype)
                        try:
                            hec.send_event(item)
                        except Exception as e:
                            log.error("error sending event: %s", e)
            time.sleep(1)

def setup(*a, **kw):
    if len(a) == 1 and isinstance(a[0], (list,tuple,)):
        a = a[0]
    return Daemon(*a, **kw)

def run(*a, **kw):
    return setup(*a, **kw).start()
