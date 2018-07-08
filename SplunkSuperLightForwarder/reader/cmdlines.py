import shlex
import subprocess
import select
import logging
import time
from SplunkSuperLightForwarder.util import RateLimit

log = logging.getLogger('sslf:cmdlines')

class Reader(object):
    default_sourcetype = 'sslf:lines'
    _last_wait = _proc = _cmd = None

    def __init__(self, cmd=None, config=None):
        if config is None:
            config = dict()
        self.config = config
        self.cmd = cmd if cmd else self.config.get('cmd')

    @property
    def cmd(self):
        return self._cmd

    @cmd.setter
    def cmd(self, cmd):
        if isinstance(cmd, (list,tuple)):
            self._cmd = cmd
            return
        if not self.died:
            log.info("changing command; killing old command")
            self.stop()
        self._cmd = shlex.split(str(cmd)) if cmd else None

    @property
    def cmd_str(self):
        return "cmd={}; pid={}".format( self.cmd, self.pid )

    def wait(self, timeout=4):
        for i in range(timeout * 2):
            if self._proc.poll() is not None:
                log.info("%s finished, issuing wait()".format(self.cmd_str))
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
        with RateLimit('start-{}'.format(self.cmd), limit=10) as rl:
            if rl:
                self.stop() # make sure we don't leave orphan procs and zombies
                self._proc = subprocess.Popen(self.cmd, stdout=subprocess.PIPE)
                log.info('started: %s', self.cmd_str)
            else:
                log.info('not starting: %s; rate limited', self.cmd_str)

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
                yield l
            elif self.died:
                self.wait()
