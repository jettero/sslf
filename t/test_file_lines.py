import os

def test_reader(tfile, file_lines, mdir):
    assert file_lines.ready is False
    tfile.my_print('supz')
    assert file_lines.ready is True
    assert [ x.event for x in file_lines.read()] == ['supz\n']
    assert file_lines.ready is False
    assert [ x.event for x in file_lines.read()] == []

    file_lines.save()
    assert os.path.isfile('t/meta/lines-reader-t_file.json') == True

    another_reader = file_lines.__class__(file_lines.path, config={'meta_data_dir': file_lines.meta_data_dir})
    assert file_lines.ready is False
    assert [ x.event for x in file_lines.read() ] == []

    import logging
    tfile.my_print("blah")
    assert file_lines.ready is True
    assert [ x.event for x in file_lines.read() ] == ['blah\n']

    tfile.my_trunc()
    tfile.my_print("yolo")
    assert file_lines.ready is True
    assert [ x.event for x in file_lines.read() ] == ['yolo\n']

def test_sig(tfile, file_lines, mdir):
    tfile.truncate(0)
    assert file_lines.gen_sig() == 'd41d8cd98f00b204e9800998ecf8427e'
