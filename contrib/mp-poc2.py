
import multiprocessing as mp
import os

class Classy:
    def __init__(self):
        self.ctx = mp.get_context('spawn')

    def f1(self, x):
        print(f'[{os.getpid()}] f1: x={x}')
        self.put(x)

    def f2(self):
        while True:
            x = self.q.get()
            if x == '______FIN':
                return
            print(f'[{os.getpid()}] f2: x={x}')

    def setup(self):
        self.q = self.ctx.Queue()
        self.p = self.ctx.Process(target=self.f2)
        return self.p

    def put(self, x):
        self.q.put(x)

    def start(self):
        self.setup()
        self.p.start()

    def join(self):
        self.put('______FIN')
        return self.p.join()

    def terminate(self):
        self.p.terminate()
        self.setup()

if __name__ == '__main__':
    c = Classy()

    # occasionally we'll get a SIGPIPE before the join() or the terminate()
    # (not really sure which). It seems to happen in the child process,
    # probably while sending a reply to the parent pid, which (probably)
    # already exited.

    c.start()
    c.f1('wut1')
    c.f1('sup1')
    print('joining')
    c.join()

    c.start()
    c.f1('wut2')
    c.f1('sup2')
    print('terminating')
    c.terminate()
