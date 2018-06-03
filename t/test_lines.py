
def test_lines(tfile, linesReader):
    assert linesReader.ready is False
    tfile.my_print('supz')
    assert linesReader.ready is True
    assert list(linesReader.read()) == ['supz\n']
    assert linesReader.ready is False
    assert list(linesReader.read()) == []
