
from sslf.returner.hec import HEC
import json

def test_payload():
    h = HEC('https://whatever', 'secret-token')
    event_dat = {'item1': 'one'}
    payload_dat = { 'time': 3, 'sourcetype': 'yeah', 'host': 'localhost', 'source': 'test-payload',
        'index': 'bs', '_jdargs': {'sort_keys': True} }

    # build hec encoding with the above
    hec_encoding = h.encode_payload(event_dat, **payload_dat)

    # reconfigure input data and encode by hand
    jdargs = payload_dat.pop('_jdargs')
    payload_dat['event'] = event_dat
    test_encoding = json.dumps(payload_dat, **jdargs).encode('utf-8')

    # they should come out the same
    assert hec_encoding == test_encoding

def test_combine():
    h1 = HEC('https://whatever', 'secret-token')
    h2 = HEC('https://revetahw', 'secret-token')
    h3 = HEC('https://whatever', 'secret-token')
    assert h1.q is not h2.q
    assert h2.q is not h3.q
    assert h1.q is     h3.q
