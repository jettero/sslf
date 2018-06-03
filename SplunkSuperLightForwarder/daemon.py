# coding: UTF-8

import importlib
import argparse
import configparser
import os
import logging

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
    paths = None

    def __init__(self, *a, **kw):
        self._grok_args(kw)
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

    def _grok_args(self, args):
        args = _dictify_args(args)
        for k in args:
            if k.startswith('_'):
                continue
            if hasattr(self,k):
                setattr(self,k, args[k])

    def _grok_path(self, path, args):
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
            self.paths[path]['reader'] = c(path)
        except ModuleNotFoundError as e:
            log.error("couldn't find {1} in {0}: {2}".format(engine,clazz,e))

    def parse_args(self, a):
        parser = argparse.ArgumentParser(description="this is program") # options and program name are automatic
        parser.add_argument('-v', '--verbose', action='store_true')
        parser.add_argument('-n', '--no-daemonize', action='store_true',
            help="don't fork and become a daemon")
        parser.add_argument('-c', '--config-file', type=str, default=self.config_file,
            help="config file (default: %(default)s)")
        args = parser.parse_args(a)
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
        import subprocess, os
        ps_cmd = 'ps wwo user,pid,rsz,vsz,stat,cmd -p {}'.format(os.getpid()).split()
        p = subprocess.Popen(ps_cmd, stdout=subprocess.PIPE)
        stdout,stderr = p.communicate()
        for line in stdout.splitlines():
            log.debug("ps listing: {}".format(line.decode()))
        return self

def setup(*a, **kw):
    if len(a) == 1 and isinstance(a[0], (list,tuple,)):
        a = a[0]
    return Daemon(*a, **kw)

def run(*a, **kw):
    return setup(*a, **kw).start()
