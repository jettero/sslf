import shlex
import subprocess
import select
import logging
import time
from sslf.reader import (
    RateLimit, AttrDict, PROC_RESTART_RLIMIT,
    ReLineEventProcessor)

log = logging.getLogger('sslf:cmdlines')

class Reader(ReLineEventProcessor):
    default_sourcetype = 'sslf:lines'
    _last_wait = _proc = _cmd = None
    shell_wrapper = False
    sleep_wrapper = False

    def __init__(self, path=None, config=None):
        if config is None:
            config = dict()
        self.path = path # more of a tag than the actual command line
        #  [/usr/bin/whatever]
        #  reader = cmdlines
        #  cmd = /usr/bin/whatever --long-arg "stuff here"
        self.cmd = config.get('cmd', path)
        self.prlimit = config.get('proc_restart_rlimit', PROC_RESTART_RLIMIT)
        self.setup_rlep(config)

        self.shell_wrapper = bool(config.get('shell_wrapper', False))
        self.sleep_wrapper = config.get('sleep_wrapper', False)
        if self.sleep_wrapper:
            try:
                self.sleep_wrapper = int( self.sleep_wrapper )
                if self.sleep_wrapper < 1:
                    self.sleep_wrapper = False
            except TypeError:
                self.sleep_wrapper = 60 if self.sleep_wrapper else False
        else:
            self.sleep_wrapper = False

    def __repr__(self):
        return f'cmdlines({self.cmd_str})'

    @property
    def cmd(self):
        if self._cmd is None:
            return None
        if self.sleep_wrapper is not False:
            c = f'while true; do {self._cmd:s}; sleep {self.sleep_wrapper:d}; done'
            return [ 'bash', '-c', c ]
        elif self.shell_wrapper:
            return ['bash', '-c', str(self._cmd)]
        return shlex.split(str(self._cmd))

    @cmd.setter
    def cmd(self, cmd):
        self._cmd = cmd
        if not self.died:
            log.info("changing command; killing old command")
            self.stop()

    @property
    def cmd_str(self):
        return f'cmd={self.cmd}; pid={self.pid}'

    def wait(self, timeout=4):
        for i in range(timeout * 2):
            if self._proc.poll() is not None:
                log.info("%s finished, issuing wait()", self.cmd_str)
                self._last_wait = self._proc.wait()
                self._proc = None
                return self._last_wait
            time.sleep(0.5)
        return False

    def stop(self):
        if not self._proc:
            return
        if self.died:
            return self.wait()
        log.info('terminating %s', self.cmd_str)
        self._proc.terminate()
        if self.wait() is not False:
            return self._last_wait
        log.info('killing %s', self.cmd_str)
        self._proc.kill()
        if self.wait() is not False:
            return self._last_wait

    def start(self):
        if not self.cmd:
            return
        # XXX: we should optionally record stderr to log.warn
        # XXX: we should optionally combine stdout+stderr
        # XXX: we should optionally stream both to different readers? maybe?
        # XXX: ... ignore for now ...
        with RateLimit(f'start-{self.cmd}', limit=self.prlimit) as rl:
            if rl:
                self.stop() # make sure we don't leave orphan procs and zombies
                self._proc = subprocess.Popen(self.cmd, stdout=subprocess.PIPE)
                log.info('started: %s', self.cmd_str)
            else:
                log.debug('not starting: %s; rate limited', self.cmd_str)

    @property
    def pid(self):
        try: return self._proc.pid
        except: pass

    @property
    def died(self):
        if not self._proc:
            return True
        return self._proc.poll() is not None

    @property
    def spoll(self):
        if not self._proc:
            return False
        return self._proc.stdout in select.select((self._proc.stdout,),tuple(),tuple(),0)[0]

    @property
    def ready(self):
        if self.spoll:
            return True
        if self.died:
            self.start()
            return self.spoll
        return False

    def read(self):
        l = True
        while self.spoll and l:
            l = self._proc.stdout.readline()
            if l:
                # error: b = bytearray([0x7f, 0x80] + [ x for x in 'lol — mang'.encode() ]); (b, b.decode()) 
                # ok, but with leading 0x7f: b.decode('utf-8', 'ignore')
                yield self.rlep_line(l.decode('utf-8', 'ignore'))
            elif self.died:
                self.wait()
