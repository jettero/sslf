
import os
import sslf.daemon

def test_config(jsonloop_daemon):
    # we can't use config_file='blah' cuz pytest freaks out
    # when we double parse the cmdline args
    assert jsonloop_daemon.config_file == 't/jsonloop.conf'
    assert len(jsonloop_daemon.paths) == 1
    assert list(jsonloop_daemon.paths)[0].split('/')[-2:] == ['t','file']

def count_file_lines(fname='t/json-return.json'):
    assert os.path.isfile(fname)
    with open(fname, 'r') as fh:
        return len( list(fh.readlines()) )

def test_step(jsonloop_daemon, thousand_line_tfile, caplog):
    jsonloop_daemon.step()
    assert list(jsonloop_daemon.paths.values())[0].hec.q.cn == 10
    assert 'aborting step early' in caplog.text
    jsonloop_daemon.step()
    assert count_file_lines() == 10
    jsonloop_daemon.step()
    assert count_file_lines() == 20
    # TODO: when we get to the point that step(), step(), step() produces the
    # right number of lines; we'll then have to make sure it's not skipping any
    # either.
