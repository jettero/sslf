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
