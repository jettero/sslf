
from sslf.re import ReEngine

TEST  = "This is my pattern 2+2=4; Nyan Cat."

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

TEST2 = {'area1': 'test pattern', 'area2': 'another test pattern'}
def test_RE2():
    area_patterns = {
        'p1:area1': r'(?P<p1k>test)\s+(?P<p1v>\S+)',
        'p2:area2': r'(?P<p2prefix>\S+)\s+(?P<p2k>test)\s+(?P<p2v>\S+)'
    }
    RE = ReEngine(**area_patterns)

    t2c = {
        'p1k': 'test',
        'p1v': 'pattern',
        'p2prefix': 'another',
        'p2k': 'test',
        'p2v': 'pattern',
    }
    t2c.update(TEST2)

    assert RE.compute_fields(TEST2) == t2c
