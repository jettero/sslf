import SplunkSuperLightForwarder

def test_setup():
    sslf = SplunkSuperLightForwarder.setup()
    assert sslf.config_file == '/etc/sslf.conf'
    sslf = SplunkSuperLightForwarder.setup('-c', 't/sslf.conf')
    assert sslf.config_file == 't/sslf.conf'
    sslf = SplunkSuperLightForwarder.setup('-c t/sslf.conf'.split())
    assert sslf.config_file == 't/sslf.conf'
