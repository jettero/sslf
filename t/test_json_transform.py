
from sslf.transform.json import JSONEventProcessor
from sslf.util import AttrDict

def test_jsont():
    t = JSONEventProcessor()
    t.setup_json(config={
        're_r2:field1': r'(?P<blah2>\w+)',
        're_r3:field2': r'(?P<blah3>\w+)',
    })
    t.path = '/supz' # normally the transforms are treated as mixins on objects with a path

    evr = t.grok_json('{"field1": "one", "field2": "two"}')
    assert isinstance(evr, AttrDict)
    assert evr.fields == {'blah2': 'one', 'blah3': 'two'}
