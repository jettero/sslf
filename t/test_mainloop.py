
import sslf.daemon

def test_mainloop(mainloop_config):
    # we can't use config_file='blah' cuz pytest freaks out
    # when we double parse the cmdline args
    d = sslf.daemon.Daemon('--config-file', 't/mainloop.conf')
    assert d.config_file == 't/mainloop.conf'
    assert len(d.paths) == 1
