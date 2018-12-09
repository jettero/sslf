
import os
import sslf.daemon

def test_config(jsonloop_daemon):
    # we can't use config_file='blah' cuz pytest freaks out
    # when we double parse the cmdline args
    assert jsonloop_daemon.config_file == 't/jsonloop.conf'
    assert len(jsonloop_daemon.paths) == 1
    assert list(jsonloop_daemon.paths)[0].split('/')[-2:] == ['t','file']

def test_step(jsonloop_daemon, thousand_line_tfile):
    jsonloop_daemon.step()
    assert list(jsonloop_daemon.paths.values())[0].hec.q.cn == 10
    jsonloop_daemon.step()
    assert os.path.isfile('t/json-return.json')
