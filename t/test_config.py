import sslf
import sys
import logging

log = logging.getLogger('sslf:test')

def test_setup(nc_config):
    sys.argv = [ sys.argv[0] ]

    log.debug("-----=: setup()")
    sslf = nc_config() # Daemon.config_file = None; Daemon().update_config()
    assert sslf.config_file == sslf.__class__.config_file

    # note that these config files aren't meant to exist
    log.debug("-----=: setup(-c t/sslf.1)")
    sslf = nc_config('-c', 't/sslf.1')
    assert sslf.config_file == 't/sslf.1'

    log.debug("-----=: setup(-c t/sslf.2)")
    sslf = nc_config('-c', 't/sslf.2')
    assert sslf.config_file == 't/sslf.2'

    log.debug("-----=: setup(config_file t/sslf.3)")
    sslf = nc_config(config_file='t/sslf.3')
    assert sslf.config_file == 't/sslf.3'

    log.debug("-----=: setup(config=t/sslf.3) --> fail")
    fail = None
    try: sslf = nc_config(config='t/sslf.3')
    except Exception as e:
        fail = e
    assert 'valid config' in str(fail)

# def test_read_file():
#     sslf = sslf.setup(config_file='t/test1.conf')
#     assert sslf.config_file == 't/test1.conf'
#     assert sslf.hec == 'https://localhost:54321/'
#     assert set(sslf.paths.keys()) == set(['/tmp/funny-little.log'])
#     assert set(sslf.paths.get('/tmp/funny-little.log',{}).keys()) == set(['re_f1', 'reader', 'hec'])
