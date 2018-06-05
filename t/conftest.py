import pytest
import os, shutil

from SplunkSuperLightForwarder.reader.lines import Reader

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
def linesReader(tfile):
    return Reader('t/file', meta_data_dir='t/meta')

@pytest.fixture
def mdir(request):
    def fin():
        if _e('NO_FIN') and _e('NO_META_FIN') and os.path.isdir('t/meta'):
            shutil.rmtree('t/meta')
    request.addfinalizer(fin)
    fin()
    return 't/meta'
