# coding: utf-8

import pytest
import os, shutil

def _e(var):
    if var in os.environ:
        l = os.environ.get(var).lower()
        if l in ('true', '1', 'yes', 't'):
            return False
    return True

@pytest.fixture
def tfile(request):
    def fin():
        if _e('NO_FIN') and _e('NO_FILE_FIN'):
            os.unlink('t/file')
    request.addfinalizer(fin)
    fh = open('t/file', 'w')
    def my_print(self,f,*a,**kw):
        self.write( f.format(*a,**kw) + '\n' )
        self.flush()
    fh.my_print = my_print.__get__(fh, fh.__class__) # bind my_print to fh
    def my_trunc(self):
        self.seek(0)
        self.truncate()
        self.flush()
    fh.my_trunc = my_trunc.__get__(fh, fh.__class__)
    return fh

@pytest.fixture
def file_lines(tfile):
    from sslf.reader.filelines import Reader
    return Reader('t/file', config={'meta_data_dir': 't/meta'})

@pytest.fixture
def mdir(request):
    def fin():
        if _e('NO_FIN') and _e('NO_META_FIN') and os.path.isdir('t/meta'):
            shutil.rmtree('t/meta')
    request.addfinalizer(fin)
    fin()
    return 't/meta'

@pytest.fixture
def nc_config():# no-[default]-config config()
    import sslf
    orig = sslf.Daemon.config_file
    sslf.Daemon.config_file = ''
    def _s(*a, **kw):
        # in test_something(nc_config), nc_config is this lambda
        # so nc_config('-c', 'whatever.conf')
        # or nc_config(config_file='blah')
        # or nc_config(config='broken') # should be config={…)
        # is handed to Daemon().update_path_config() here:
        return sslf.Daemon(*a, **kw).update_path_config()
    yield _s
    sslf.Daemon.config_file = orig


@pytest.fixture
def jsonloop_config():
    with open('t/_jsonloop.conf', 'r') as infh:
        with open('t/jsonloop.conf', 'w') as outfh:
            for line in infh.readlines():
                outfh.write(line.replace('<PWD>', os.getcwd()))
