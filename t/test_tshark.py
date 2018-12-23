
import pytest
import simplejson as json

from sslf.reader.tshark import Reader as tshark
from sslf.transform.tsharkek import dedup_key_prefixes

def test_dedup_kp():
    input = {'lol': 'wut', 'lol_supz_mang': 'mang', 'lol_supz_dood': 'dood', 'long_key_thing': 'thing', 'long_key_other': 'other' }
    output = {'lol': {'val': 'wut', 'supz': {'mang': 'mang', 'dood': 'dood'}},
        'long_key': {'other': 'other', 'thing': 'thing'},
    }
    assert dedup_key_prefixes(input) == output

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

    # this test is kindof pointless... I just wrote out the sample to a file
    # eyeballed it to see if it was shaped how I wanted ...  then we check to
    # see if the process that generated the file generates the file
    #
    # 4. ?profit?

    assert pp == tshark_jpp_json
