import sys
import logging
import pytest

import sslf
from sslf.daemon import DaemonConfig

log = logging.getLogger('sslf:test')

sys.argv = [ sys.argv[0] ]

def test_setup1(nc_config):
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
    with pytest.raises(DaemonConfig, message="Expecting DaemonConfig error", match=r'.*?valid config.*'):
        sslf = nc_config(config='t/sslf.3')
