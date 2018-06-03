import SplunkSuperLightForwarder

def test_setup():
    sslf = SplunkSuperLightForwarder.setup()
    assert sslf.config_file == SplunkSuperLightForwarder.Daemon.config_file

    sslf = SplunkSuperLightForwarder.setup('-c', 't/sslf.1')
    assert sslf.config_file == 't/sslf.1'

    sslf = SplunkSuperLightForwarder.setup('-c t/sslf.2'.split())
    assert sslf.config_file == 't/sslf.2'

    sslf = SplunkSuperLightForwarder.setup(config_file='t/sslf.3')
    assert sslf.config_file == 't/sslf.3'
