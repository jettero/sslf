
from sslf.re import ReEngine

def test_RE():
    TEST = "This is my pattern 2+2=4; Nyan Cat."
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

def test_RE2():
    TEST2 = {'area1': 'test pattern', 'area2': 'another test pattern'}
    area_patterns = {
        'p1': '(?P<v0>another test pattern)',
        'p2:area1': r'(?P<k2>test)\s+(?P<v2>\S+)',
        'p3:area2': r'(?P<prefix>\S+)\s+(?P<k3>test)\s+(?P<v3>\S+)'
    }
    RE = ReEngine(**area_patterns)

    t2c = {
        'v0': 'another test pattern',
        'k2': 'test',
        'v2': 'pattern',
        'prefix': 'another',
        'k3': 'test',
        'v3': 'pattern',
    }
    t2c.update(TEST2)

    assert RE.compute_fields(TEST2) == t2c
