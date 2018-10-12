
import multiprocessing as mp
import os, time

def f1(x, q):
    print(f'[{os.getpid()}] f1: x={x}')
    q.put(x)

def f2(q):
    while True:
        x = q.get()
        print(f'[{os.getpid()}] f2: x={x}')
        if x == '______FIN':
            return

if __name__ == '__main__':
    ctx = mp.get_context('spawn')
    q = ctx.Queue()
    p = ctx.Process(target=f2, args=(q,))
    p.start()
    f1(7, q)
    f1('______FIN', q)
    p.join()
    p = ctx.Process(target=f2, args=(q,))
    p.start()
    f1(7, q)
    time.sleep(0.25)
    p.terminate()
