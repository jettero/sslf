
import sslf.daemon

def test_step(jsonloop_config):
    # we can't use config_file='blah' cuz pytest freaks out
    # when we double parse the cmdline args
    d = sslf.daemon.Daemon('--config-file', 't/jsonloop.conf')
    assert d.config_file == 't/jsonloop.conf'
    assert len(d.paths) == 1
    assert list(d.paths)[0].split('/')[-2:] == ['t','file']
