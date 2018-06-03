#!/usr/bin/env python3

# NOTE: this isn't actually installed by setup.py it's just here for convenient
#       ./sslf.py runs directly in the repo directory

import SplunkSuperLightForwarder

if __name__ == '__main__':
    sslf = SplunkSuperLightForwarder.Daemon()
    sslf.start()
