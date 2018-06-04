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

    import logging
    tfile.my_print("blah")
    assert linesReader.ready is True
    assert list(linesReader.read()) == ['blah\n']

    tfile.my_trunc()
    tfile.my_print("yolo")
    assert linesReader.ready is True
    assert list(linesReader.read()) == ['yolo\n']

def test_sig(tfile, linesReader, mdir):
    tfile.truncate(0)
    assert linesReader.gen_sig() == 'd41d8cd98f00b204e9800998ecf8427e'
