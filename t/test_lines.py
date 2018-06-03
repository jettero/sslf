import os

def test_lines(tfile, linesReader, mdir):
    assert linesReader.ready is False
    tfile.my_print('supz')
    assert linesReader.ready is True
    assert list(linesReader.read()) == ['supz\n']
    assert linesReader.ready is False
    assert list(linesReader.read()) == []

    linesReader.save()
    assert os.path.isfile('t/meta/lines-reader-t_file.json') == True

    another_reader = linesReader.__class__(linesReader.path, meta_data_dir=linesReader.meta_data_dir)
    assert linesReader.ready is False
    assert list(linesReader.read()) == []
