
from sslf.util import AttrDict
from sslf.returner.hec import HEC
import simplejson as json

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

    # Lastly, make sure if we give an AttrDict(event='blah') to h.encode_payload(),
    # it still does the right thing(s)
    evr = AttrDict(event='supz mang', time=24, source='/something/strange',
        host='localhost', fields={'lolol': 'yes'})
    epb = h.encode_payload(evr)
    hep = json.loads(epb.decode('utf-8'))
    assert hep == { 'event': 'supz mang', 'source': '/something/strange',
        'fields': {'lolol': 'yes'}, 'index': 'main', 'sourcetype': 'json',
        'time': 24, 'host': 'localhost' }

    # still the right thing if the time is in the event
    evr = AttrDict(event={'msg': 'supz mang', 'time': 24},
        source='/something/strange', host='localhost', fields={'lolol': 'yes'})
    epb = h.encode_payload(evr)
    hep = json.loads(epb.decode('utf-8'))
    assert hep == { 'event': {'msg': 'supz mang', 'time': 24}, 'source':
        '/something/strange', 'fields': {'lolol': 'yes'}, 'index': 'main',
        'sourcetype': 'json', 'time': 24, 'host': 'localhost' }

    # still the right thing if the time is in the extracted fields
    evr = AttrDict(event='supz mang', source='/something/strange', host='localhost',
        fields={'lolol': 'yes', 'time': 24})
    epb = h.encode_payload(evr)
    hep = json.loads(epb.decode('utf-8'))
    assert hep == { 'event': 'supz mang', 'source': '/something/strange',
        'fields': {'time': 24, 'lolol': 'yes'}, 'index': 'main',
        'sourcetype': 'json', 'time': 24, 'host': 'localhost' }

def test_combine():
    h1 = HEC('https://whatever', 'secret-token')
    h2 = HEC('https://revetahw', 'secret-token')
    h3 = HEC('https://whatever', 'secret-token')
    assert h1.q is     h3.q
    assert h1.q is not h2.q
    assert h2.q is not h3.q
