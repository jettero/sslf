import pytest

from SplunkSuperLightForwarder.reader.cmdlines import Reader as cl
import time

ctxt = 'ls -al {}'.format(__file__)

def _wait_for_startup(c, t=2):
    for i in range(10 * t):
        if c.ready:
            break
        time.sleep(0.1)

def _assert_things(c):
    assert c.cmd[-1] == __file__
    assert c.pid is None
    assert c.died is True
    _wait_for_startup(c)
    assert c.ready is True
    assert c.spoll is True
    lines = list(c.read())
    assert len(lines) == 1
    assert __file__ in lines[0].event
    assert c.died is True
    assert c.spoll is False
    lines = list(c.read())
    assert len(lines) == 0
    assert c.died is True
    assert c.spoll is False

@pytest.mark.order1
def test_reader_path_as_cmd():
    c = cl(ctxt, config={'proc_restart_rlimit': 0})
    _assert_things(c)

@pytest.mark.order2
def test_reader_rate_limited():
    c = cl(ctxt, config={'proc_restart_rlimit': 300})
    _wait_for_startup(c)
    assert c.ready is False # rate limiting

@pytest.mark.order3
def test_reader_path_and_cmd_rlimited():
    # this same command can't really start up again yet
    # (default rlimit is 60 seconds, we specifiy to make the test clear)
    c = cl('/bin/ls', config={'cmd': ctxt, 'proc_restart_rlimit': 0})
    _assert_things(c)

def wrappers():
    c0 = cl(config={'sleep_wrapper': False, 'shell_wrapper': False})
    c1 = cl(config={'sleep_wrapper': False, 'shell_wrapper': True })
    c2 = cl(config={'sleep_wrapper': 10,    'shell_wrapper': False})
    c3 = cl(config={'sleep_wrapper': 10,    'shell_wrapper': True })

    cmd = 'pgrep -f sslf.py | ps ho rss'
    c0.cmd = cmd
    assert c0.cmd == cmd.split()

    c1.cmd = cmd
    assert c1.cmd == ['bash', '-c'] + cmd

    c2.cmd = cmd
    assert c2.cmd == ['bash', '-c', 'while true; do {}; sleep 10; done'.format(cmd) ]

    c3.cmd = cmd
    assert c3.cmd == ['bash', '-c', 'while true; do {}; sleep 10; done'.format(cmd) ]
