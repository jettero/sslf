# coding: utf-8

import pytest
import os, shutil
import importlib
import sslf.daemon

def _e(var):
    if var in os.environ:
        l = os.environ.get(var).lower()
        if l in ('true', '1', 'yes', 't'):
            return False
    return True

@pytest.fixture
def tfile(request):
    def fin():
        if _e('NO_FIN') and _e('NO_FILE_FIN') and os.path.isfile('t/file'):
            os.unlink('t/file')
    fin()
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
    sslf.daemon.Daemon.config_file = ''
    def _s(*a, **kw):
        # in test_something(nc_config), nc_config is this lambda
        # so nc_config('-c', 'whatever.conf')
        # or nc_config(config_file='blah')
        # or nc_config(config='broken') # should be config={…)
        # is handed to Daemon().update_path_config() here:
        return sslf.daemon.Daemon(*a, **kw).update_path_config()
    yield _s
    importlib.reload(sslf.daemon)


@pytest.fixture
def jsonloop_config(request):
    with open('t/_jsonloop.conf', 'r') as infh:
        with open('t/jsonloop.conf', 'w') as outfh:
            for line in infh.readlines():
                outfh.write(line.replace('<PWD>', os.getcwd()))
    def fin():
        if _e('NO_FIN') and _e('NO_JSONLOOP_FIN'):
            os.unlink('t/jsonloop.conf')
    request.addfinalizer(fin)
    return 't/jsonloop.conf'

@pytest.fixture
def jsonloop_daemon(jsonloop_config, mdir):
    yield sslf.daemon.Daemon('--config-file', jsonloop_config)
    importlib.reload(sslf.daemon)

@pytest.fixture
def thousand_line_tfile(tfile):
    for i in range(0,1000):
        tfile.my_print(f'line-{i}')
    return tfile
