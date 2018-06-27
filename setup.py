#!/usr/bin/env python

import sys
from distutils.core import setup
from setuptools.command.test import test as TestCommand

class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to pytest")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ''

    def run_tests(self):
        import shlex
        import pytest
        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)

setup(name='splunk-super-light-forwarder',
    version       = '1.0',
    description   = 'Splunk Super Light Forwarder',
    author        = 'Paul Miller',
    author_email  = 'paul@jettero.pl',
    url           = 'https://github.com/jettero/sslf',
    py_modules    = ['SplunkSuperLightForwarder'],
    tests_require = ['pytest', 'pytest-pythonpath'],
    cmdclass      = {'test': PyTest},
    entry_points={
        'console_scripts': [
            'sslf = SplunkSuperLightForwarder:run',
        ],
    },
)

