#!/usr/bin/env python3
# coding: UTF-8

import argparse

class SplunkSuperLightForwarder(object):
    verbose = False
    daemonize = False

    def __init__(self, **kw):
        self._grok_args(kw)

    def _grok_args(self, args):
        d = args.__dict__ if isinstance(args, argparse.Namespace) else args
        for k in d:
            if k.startswith('_'):
                continue
            if hasattr(self,k):
                setattr(self,k, getattr(args,k))

    def start(self):
        pass

    def parse_args(self, *a, **kw):
        parser = argparse.ArgumentParser(description="this is program") # options and program name are automatic
        parser.add_argument('-v', '--verbose',   action='store_true')
        parser.add_argument('-d', '--daemonize', action='store_true')

        args = parser.parse_args(*a, **kw)
        self._grok_args(args)

    def start(self):
        pass

if __name__ == '__main__':
    sslf = SplunkSuperLightForwarder()
    sslf.parse_args()
    sslf.start()
