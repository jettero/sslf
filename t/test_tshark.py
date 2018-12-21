
from sslf.reader.tshark import Reader as tshark

def test_cmd1():
    c0 = tshark(config={
        'local_dst': 'ld',
        'local_src': 'ls',
        'tcp_syn':   'MAH_FLAGS',
        'interface': 'wooterface',
    })

    assert c0.cmd == [
        'tshark', '-i', 'wooterface', '-T', 'ek',
        '-f', 'MAH_FLAGS and ((ls and not ld) or (ld and not ls))',
        '-j', 'ip', '-n' ]

    assert c0.parse_time == 'timestamp'

