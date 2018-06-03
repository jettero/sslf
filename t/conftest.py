import pytest
import os

from SplunkSuperLightForwarder.engine.lines import Reader

@pytest.fixture
def tfile(request):
    def fin():
        os.unlink('t/file')
    request.addfinalizer(fin)
    fh = open('t/file', 'w')
    def my_print(self,f,*a,**kw):
        self.write( f.format(*a,**kw) + '\n' )
        self.flush()
    fh.my_print = my_print.__get__(fh, fh.__class__) # bind my_print to fh
    return fh

@pytest.fixture
def linesReader(tfile):
    return Reader('t/file')
