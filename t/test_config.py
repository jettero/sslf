import SplunkSuperLightForwarder
import sys

def test_setup():
    sys.argv = [ sys.argv[0] ]

    sslf = SplunkSuperLightForwarder.setup()
    assert sslf.config_file == SplunkSuperLightForwarder.Daemon.config_file

    sslf = SplunkSuperLightForwarder.setup('-c', 't/sslf.1')
    assert sslf.config_file == 't/sslf.1'

    sslf = SplunkSuperLightForwarder.setup('-c t/sslf.2'.split())
    assert sslf.config_file == 't/sslf.2'

    sslf = SplunkSuperLightForwarder.setup(config_file='t/sslf.3')
    assert sslf.config_file == 't/sslf.3'

    fail = None
    try: sslf = SplunkSuperLightForwarder.setup(config='t/sslf.3')
    except Exception as e:
        fail = e
    assert 'valid config' in str(fail)

def test_read_file():
    sslf = SplunkSuperLightForwarder.setup(config_file='t/test1.conf')
    assert sslf.config_file == 't/test1.conf'
    assert sslf.hec == 'https://localhost:54321/'
    assert set(sslf.paths.keys()) == set(['/tmp/funny-little.log'])
    assert set(sslf.paths.get('/tmp/funny-little.log',{}).keys()) == set(['re_f1', 'reader'])
