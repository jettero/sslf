
import os
import simplejson as json
import sslf.daemon

def test_config(jsonloop_daemon):
    # we can't use config_file='blah' cuz pytest freaks out
    # when we double parse the cmdline args
    assert jsonloop_daemon.config_file == 't/jsonloop.conf'
    assert len(jsonloop_daemon.paths) == 1
    assert list(jsonloop_daemon.paths)[0].split('/')[-2:] == ['t','file']

def count_file_lines(fname='t/json-return.json'):
    try:
        with open(fname, 'r') as fh:
            return len( list(fh.readlines()) )
    except:
        return 0

def retrieve_file_lines(fname='t/file'):
    with open(fname, 'r') as fh:
        for line in fh.readlines():
            yield line.rstrip()

def retrieve_json_events(fname='t/json-return.json'):
    for line in retrieve_file_lines(fname):
        pline = json.loads(line)
        yield pline['event'].rstrip()

def test_step(jsonloop_daemon, thousand_line_tfile, caplog):
    jsonloop_daemon.step()
    assert list(jsonloop_daemon.paths.values())[0].hec.q.cn == 10
    assert 'aborting step early' in caplog.text
    jsonloop_daemon.step()
    assert count_file_lines() == 10
    for line,event in zip(retrieve_file_lines(), retrieve_json_events()):
        assert line == event
    jsonloop_daemon.step()
    assert count_file_lines() == 20
