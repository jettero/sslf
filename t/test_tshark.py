
import pytest
import simplejson as json

from sslf.reader.tshark import Reader as tshark

@pytest.fixture
def tshark_json():
    with open('t/tshark.json', 'r') as fh:
        yield json.load(fh)

def test_cmd1(tshark_json):
    c0 = tshark(config={
        'local_dst': 'ld',
        'local_src': 'ls',
        'tcp_syn':   'MAH_FLAGS',
        'interface': 'wooterface',
        'out_proto': 'ip tcp'
    })

    assert c0.cmd == [
        'tshark', '-i', 'wooterface', '-T', 'ek',
        '-f', 'MAH_FLAGS and ((ls and not ld) or (ld and not ls))',
        '-j', 'ip tcp', '-n' ]

    assert c0.parse_time == 'timestamp'

    pp = c0.json_post_process(tshark_json)
    ppe = pp['event']
    tsl = tshark_json['layers']
    assert 'ip' in ppe
    assert 'ip' in tsl

    for p in ('ip', 'tcp'):
        c = 0
        for k in tsl[p]:
            pr = f'{p}_'
            prpr = f'{pr}{pr}'
            if k.startswith(prpr):
                m = k[len(prpr):]
                assert ppe[p][m] == tsl[p][k]
                c += 1
            elif k.startswith(pr):
                m = k[len(pr):]
                assert ppe[p][m] == tsl[p][k]
                c += 1
        assert len(ppe[p]) == c
