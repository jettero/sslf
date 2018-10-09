
from sslf.returner.hec import Payload

def test_payload():
    p1 = Payload('item1', 'item2', 'item3')
    p2 = Payload('item1', 'item2', 'item3')
    p3 = Payload('item1', 'item2', 'item3')

    p3.max_bytes = 7
    p2.max_bytes = 13

    m1 = list(p1)
    m2 = list(p2)
    m3 = list(p3)

    assert len(m1) == 1
    assert len(m2) == 2
    assert len(m3) == 3

    assert m1[0] == b'item1 item2 item3'
    assert m2[0] == b'item1 item2'
    assert m2[1] == b'item3'
    assert m3[0] == b'item1'
    assert m3[1] == b'item2'
    assert m3[2] == b'item3'
