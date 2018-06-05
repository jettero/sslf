
import daemonize, sys, os, time

c = 0
def logpid(a=None):
    global c
    c += 1
    with open('/tmp/funny-little.log', 'a') as fh:
        fh.write("supz {}-{} {}\n".format(a, c, os.getpid()))

logpid('a')
def main():
    logpid('b')
    time.sleep(2)
d = daemonize.Daemonize(app='blah', pid='/tmp/file.pid', action=main)
d.start()
logpid('c')
