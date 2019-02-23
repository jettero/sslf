# coding: UTF-8

import argparse
import configparser
import os, sys
import logging
import time
import signal
import daemonize
import collections
import re

from sslf.returner import HEC
from sslf.util import (AttrDict, AttrProxyList, RateLimit, build_tzinfos,
    DEFAULT_MEMORY_SIZE, DEFAULT_DISK_SIZE, find_namespaced_class)

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
    one_step = False
    config_file = '/etc/sslf.conf'
    meta_data_dir = '/var/cache/sslf'
    paths = None
    hec = None
    token = None
    index = None
    sourcetype = None
    logger = log
    tz_load_re = '^(GMT|UTC)|^(US|Europe|Asia)/'
    step_interval = 0.5 # sleep seconds between step()s
    step_runtime_max = 2 # max time in step() before loop break
    record_age_filter = 2000000 # 2 Msec is roughly 23 days

    log_level     = 'info'
    log_file      = '/var/log/sslf.log'
    log_fmt_cli   = '%(name)s [%(process)d] %(levelname)s: %(message)s'
    log_fmt       = '%(asctime)s ' + log_fmt_cli

    use_certifi = True

    _path_config = dict()

    disk_queue = None
    mem_queue_size = DEFAULT_MEMORY_SIZE
    disk_queue_size = DEFAULT_DISK_SIZE

    returner = HEC

    verify_ssl = True

    _fields = (
        'verbose', 'daemonize', 'config_file', 'meta_data_dir',
        'hec','token','index','sourcetype', 'pid_file',
        'log_level', 'log_file', 'log_fmt_cli', 'log_fmt',
        'tz_load_re', 'step_runtime_max', 'step_interval', 'disk_queue',
        'mem_queue_size', 'disk_queue_size', 'verify_ssl', 'use_certifi',
        'returner', 'record_age_filter', 'one_step'
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

        self._debug_run_too_long_delay = False

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
                nv = args[k]
                ov = getattr(self, k)
                ga_t = None if ov is None else type(ov)
                if k == 'returner':
                    nv = find_namespaced_class(nv, 'sslf.returner', 'Returner')
                elif ga_t is bool and isinstance(nv, (str,)):
                    if nv.lower() in ('false', 'no', '0',): nv = False
                    elif nv.lower() in ('true', 'yes', '1',): nv = True
                elif ga_t is not None:
                    nv = ga_t(nv)
                setattr(self, k, nv)
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
            pv = AttrDict()
        pv.update(args)
        class RetryBackoff(AttrDict):
            def __str__(self):
                return f'skip_steps={self.n} step_count={self.c}'
        pv['retry_backoff'] = RetryBackoff(n=0, c=0)

        if not pv.get('meta_data_dir'):
            pv['meta_data_dir'] = self.meta_data_dir

        pv['reader'] = find_namespaced_class(pv.pop('reader','lines'),
            'sslf.reader', 'Reader')(path, config=pv)
        if 'returner' in pv:
            pv['returner'] = find_namespaced_class(pv['returner'], 'sslf.returner', 'Returner')

        def sourcetype_filter(x):
            if x:
                return x
            try:
                return pv['reader'].default_sourcetype
            except AttributeError:
                pass
            return 'sslf:' + module.split('.')[-1]

        def disk_queue_fix(x):
            if x is None or not x.strip():
                return
            if x == self.meta_data_dir:
                return os.path.join(self.meta_data_dir, 'dq')
            if x.startswith('/'):
                return x
            return os.path.join(self.meta_data_dir, x)

        apl = AttrProxyList(pv, self,
            sourcetype=sourcetype_filter,
            index=lambda x: x or 'tmp',
            disk_queue=disk_queue_fix,
            )

        if not apl.hec or not apl.token or not apl.index:
            logsafe_token = re.sub(r'[^-]','x', apl.token or '') or 'None'
            log.warning("invalid hec settings path=%s, hec=%s, token=%s, index=%s, skipping",
                path, apl.hec, logsafe_token, apl.index)
            return

        pv['hec'] = apl.returner( apl.hec, apl.token,
            verify_ssl=apl.verify_ssl, use_certifi=apl.use_certifi,
            mem_size=apl.mem_queue_size, disk_queue=apl.disk_queue, disk_size=apl.disk_queue_size,
            record_age_filter=apl.record_age_filter,
            base_payload={'sourcetype': apl.sourcetype, 'index': apl.index},
        )

        self.paths[path] = pv

    def parse_args(self, a):
        parser = argparse.ArgumentParser(description="this is program") # options and program name are automatic
        parser.add_argument('-V', '--version', action='store_true', help="print version and exit")
        parser.add_argument('-v', '--verbose', action='store_true')
        parser.add_argument('-f', '--daemonize', action='store_true', help="fork and become a daemon")
        parser.add_argument('-l', '--log-level', type=str, default=self.log_level,
            help="daemon logging level (default: %(default)s)")
        parser.add_argument('-c', '--config-file', type=str, default=self.config_file,
            help="config file (default: %(default)s)")
        parser.add_argument('-m', '--meta-data-dir', type=str, default=self.meta_data_dir,
            help="location of meta data (default: %(default)s)")
        parser.add_argument('--show-config', action='store_true', help='show the final daemon config and exit')
        parser.add_argument('-o', '--opt', nargs='*', default=tuple(),
            help='supply daemon options (eg): -o index=tmp use_certifi=false')
        parser.add_argument('-p', '--path', nargs='*', default=tuple(),
            help='override path configs with the form /location:opt=val,opt=val')
        args = parser.parse_args(a) if a else parser.parse_args()
        if args.version:
            try:
                from . version import version
                print(version)
            except:
                print("unknown")
            sys.exit(0)
        self._grok_args(args)

        if args.show_config:
            self.read_config()

        if args.opt:
            additional_args = dict()
            for o in args.opt:
                try:
                    k,v = o.split('=')
                    additional_args[k] = v
                except ValueError as e:
                    raise Exception(f'--opt {o} not understood') from e
                if k not in self._fields:
                    raise Exception(f'--opt {o} unknown field')
            if additional_args:
                self._grok_args(additional_args)

        if args.path:
            self._path_config = dict()
            for p in args.path:
                s = p.split(':')
                p = s.pop(0)
                d = dict()
                if s:
                    s = s[0]
                    for o in s.split(','):
                        try:
                            k,v = o.split('=')
                            d[k] = v
                        except ValueError as e:
                            raise Exception(f'{p}:{o} not understood') from e
                self._path_config[p] = d

        if args.show_config:
            self.update_path_config()
            m = max([ len(i) for i in self._fields ]) + 1
            for f in self._fields:
                fh = f + ':'
                v = getattr(self, f)
                print(f'{fh:{m}} {v}')
            for path in self.paths:
                print(f'\n{path}:')
                m = max([ len(i) for i in self.paths[path] ]) + 1
                for k,v in self.paths[path].items():
                    kh = k + ':'
                    print(f'    {kh:{m}} {v}')
            sys.exit(0)

    @classmethod
    def _config_reader(self):
        config = configparser.ConfigParser(
            allow_no_value=True,
            delimiters=('=',),
            inline_comment_prefixes=('#',),
            comment_prefixes=('#',),
            interpolation=configparser.ExtendedInterpolation(),
        )

        class G:
            cb = {
                'pid': os.getpid,
                'uid': os.getuid,
                'uid': os.getgid,
                'cwd': os.getcwd,
                'pwd': os.getcwd,
                }
            def __getitem__(self, name):
                if name in self.cb:
                    return self.cb()

            def items(self):
                for k in self.cb:
                    yield (k, self.cb[k]())
        config['G'] = G()

        def gigity(x):
            s = x.split(':')
            s[0] = s[0].lower()
            return ':'.join(s)
        config.optionxform = gigity

        return config

    def read_config(self):
        if not self.config_file:
            return

        config = self._config_reader()

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

    @property
    def run_too_long(self):
        if self._debug_run_too_long_delay:
            log.info("debug_run_too_long_delay time.sleep(%0.2f)", self._debug_run_too_long_delay)
            time.sleep(self._debug_run_too_long_delay)
        srs = self.step_runtime_start
        if srs < 0:
            return True
        if srs > 0:
            if (time.time()-srs) > self.step_runtime_max:
                self.start_runtime_timer(-1)
                return True
        return False

    @property
    def step_runtime_start(self):
        try: return self._step_runtime_start
        except: pass
        return self.start_runtime_timer()

    def start_runtime_timer(self, v=None):
        self._step_runtime_start = v if v is not None else time.time()
        return self._step_runtime_start

    def step(self):
        step_unfinished = False

        log.debug('------------------------------ STEP ------------------------------')
        self.start_runtime_timer()

        done = set()
        for pv in self.paths.values():
            if pv.hec.q.cn < 1:
                continue

            if pv.hec.q in done:
                continue
            done.add(pv.hec.q)
            step_unfinished = True

            log.debug('%s %s has events to flush, flushing', pv.reader, pv.hec)

            rb = pv['retry_backoff']
            # rb.n is the number of steps we should skip flush for this queue
            # rb.c is the number of steps we actually skipped the flush for this queue
            if rb.c < rb.n:
                rb['c'] += 1
                log.debug("%s is in backoff (%s)", pv.hec.url, rb)
                continue

            if pv.hec.flush().ok:
                if rb.n > 0:
                    log.info("flush ok, canceling backoff for %s", pv.hec.url)
                rb['n'] = rb['c'] = 0

            else:
                rb['n'] = rb.n * 2 if rb.n > 0 else 2
                rb['c'] = 0
                log.info("setting %s to backoff (skip_steps: %s)", pv.hec.url, rb.n)

        for pv in self.paths.values():
            event_count,queued_count,filtered_count,rejected_count = 0,0,0,0
            if pv.reader.ready:
                step_unfinished = True
                log.debug("%s says its ready, reading", pv.reader)
                for evr in pv.reader.read():
                    log.debug("received event from %s, queueing for hec %s", pv.reader, pv.hec)
                    try:
                        # NOTE: if queue_event() is untrue, the event was filtered
                        res = pv.hec.queue_event(evr)
                        event_count += 1
                        if res is True:    queued_count   += 1
                        elif res is False: filtered_count += 1
                        else:              rejected_count += 1
                    except Exception as e:
                        log.error("error queueing event for %s: %s", pv.hec, e)
                    if self.run_too_long:
                        log.debug('step_runtime_max=%d reached', self.step_runtime_max)
                        # NOTE: we only break the inner loop so each reader can
                        # emit at least one item per loop
                        break
                    if rejected_count > 1:
                        log.error('queue rejected more than one item, aborting read')
                        break
                if event_count > 0:
                    log.info("%s -> %s; events=%d filtered=%d rejected=%d queued=%d",
                        pv.reader.path, pv.hec.url,
                        event_count, filtered_count,
                        rejected_count, queued_count)

        return step_unfinished

    def loop(self):
        if self.paths:
            while True:
                if not self.step():
                    if self.one_step:
                        log.info("one_step is set and all paths seem to have completed")
                        return
                time.sleep(self.step_interval)
        else:
            log.error('no paths configured, nothing to do')

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
            log.warning('sending SIGTERM to other sslf pid=%d', pid)
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
