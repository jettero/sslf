
from sslf.util.cimport import (mod_cls_split, find_namespaced_class)

def test_cls_split():
    assert mod_cls_split('lines', 'sslf.reader', 'Reader') == ('sslf.reader.lines', 'Reader')
    assert mod_cls_split('lines.Thingy', 'sslf.reader', 'Reader') == ('sslf.reader.lines', 'Thingy')
    assert mod_cls_split('hec.HEC', 'sslf.returner', 'Returner') == ('sslf.returner.hec', 'HEC')
    assert mod_cls_split('json', 'sslf.returner', 'Returner') == ('sslf.returner.json', 'Returner')

def test_find_object():
    c = find_namespaced_class('hec', 'sslf.returner', 'Returner')
    from sslf.returner.hec import Returner as hr
    assert c is hr
