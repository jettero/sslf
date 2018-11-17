
from sslf.re import ReEngine

def test_RE_str():
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

def test_RE_dict():
    TEST2 = {'area1': 'test pattern', 'area2': 'another test pattern'}
    area_patterns = {
        'p1:area1': r'(?P<a11>test)\s+(?P<a12>\S+)',
        'p2:area2': r'(?P<a21>\S+)\s+(?P<a22>test)\s+(?P<a23>\S+)'
    }
    RE = ReEngine(**area_patterns)

    t2c = {
        'a11': 'test',
        'a12': 'pattern',
        'a21': 'another',
        'a22': 'test',
        'a23': 'pattern',
    }

    assert RE.compute_fields(TEST2) == t2c
