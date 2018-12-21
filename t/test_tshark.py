
import pytest
import simplejson as json

from sslf.reader.tshark import Reader as tshark

@pytest.fixture
def tshark_json():
    with open('t/tshark.json', 'r') as fh:
        yield json.load(fh)

@pytest.fixture
def tshark_jpp_json():
    with open('t/tshark_jpp.json', 'r') as fh:
        yield json.load(fh)

@pytest.fixture
def c0():
    return tshark(config={
        'local_dst': 'ld',
        'local_src': 'ls',
        'tcp_syn':   'MAH_FLAGS',
        'interface': 'wooterface',
        'out_proto': 'ip tcp'
    })

def test_cmd(c0):
    assert c0.cmd == [
        'tshark', '-i', 'wooterface', '-T', 'ek',
        '-f', 'MAH_FLAGS and ((ls and not ld) or (ld and not ls))',
        '-j', 'ip tcp', '-n' ]
    assert c0.parse_time == 'timestamp'

def test_post_processing(c0, tshark_json, tshark_jpp_json):
    pp = c0.json_post_process(tshark_json)

    assert pp == tshark_jpp_json
