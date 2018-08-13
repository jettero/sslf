
from sslf.re import ReEngine

TEST = "This is my pattern 2+2=4; Nyan Cat."

def test_RE():
    RE = ReEngine(p1=r'(is).*Cat')
    assert RE.compute_fields(TEST) == {1: 'is'}

    RE.set_re(p1=r'(?P<one>is).*(Cat)')
    assert RE.compute_fields(TEST) == {'one': 'is'}

    more_complicated = {
        'p1': '(?P<one>.*);',
        'p2:one': r'(?P<two>\S+)$',
        'p3': r'(?P<cat>.at)\.',
        'p4:two': r'(.)',
    }

    RE.set_re(**more_complicated)
    assert RE.compute_fields(TEST) == {
        'one': TEST.split(';')[0],
        'two': '2+2=4',
        'cat': 'Cat',
        1: '2',
    }
