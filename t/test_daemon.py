
import os
import simplejson as json
import logging

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

def test_step(jsonloop_daemon, thousand_line_tfile):
    path_key  = list(jsonloop_daemon.paths)[0]
    path_item = jsonloop_daemon.paths[path_key]
    for i in range(0,100):
        log.debug('-- jsonloop_daemon.step() i=%d', i)
        jsonloop_daemon.step()
        qcn = path_item.hec.q.cn
        fcn = count_file_lines()
        assert {'qcn': qcn, 'fcn': fcn} == {'qcn': 10, 'fcn': i*10}
        assert path_item.reader.ready == True

    jsonloop_daemon.step()
    for sline,revent in zip(retrieve_file_lines(), retrieve_json_events()):
        log.debug('sline=%s == revent=%s', sline, revent)
        assert sline == revent
    qcn = path_item.hec.q.cn
    fcn = count_file_lines()
    assert {'qcn': qcn, 'fcn': fcn} == {'qcn': 0, 'fcn': 1000}
    assert path_item.reader.ready == False
