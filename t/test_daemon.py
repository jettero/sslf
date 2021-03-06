
import time
import os
import simplejson as json
import logging
import pytest

import sslf.daemon

log = logging.getLogger(__name__)

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

def _measure_timings():
    now = time.time()
    for i in range(0,10):
        time.sleep(0.1)
    dt = time.time() - now
    if abs(dt - 1) < 0.1:
        return False
    return True

@pytest.mark.skipif(_measure_timings(), reason="timing based tests in inconsistent environment")
def test_step(jsonloop_daemon, thousand_line_tfile):
    path_key  = list(jsonloop_daemon.paths)[0]
    path_item = jsonloop_daemon.paths[path_key]

    # NOTE: before step_runtime_max, I experimented with step_msg_limit to limit
    # the number of events that could be processed per step() … that was relatively
    # easy to test, but the timing based limits aren't so easy to test and so
    # this test may generate false-failures from time to time …
    jsonloop_daemon._debug_run_too_long_delay = 0.1
    assert jsonloop_daemon.log_file == 't/sslf.log'
    try: jds_loops = int(os.environ.get('JDS_LOOPS', 3))
    except: jds_loops = 3

    for i in range(0, jds_loops):
        log.debug('-- jsonloop_daemon.step() i=%d', i)
        jsonloop_daemon.step()
        qcn = path_item.hec.q.cn
        fcn = count_file_lines()
        assert {'qcn': qcn, 'fcn': fcn} == {'qcn': 10, 'fcn': i*10}
        assert path_item.reader.ready == True

    jsonloop_daemon._debug_run_too_long_delay = 0
    for i in range(1,10):
        jsonloop_daemon.step()
    qcn = path_item.hec.q.cn
    fcn = count_file_lines()
    assert {'qcn': qcn, 'fcn': fcn} == {'qcn': 0, 'fcn': 1000}
    assert path_item.reader.ready == False

    for sline,revent in zip(retrieve_file_lines(), retrieve_json_events()):
        log.debug('sline=%s == revent=%s', sline, revent)
        assert sline == revent
