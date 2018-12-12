PYTHON := $(shell which python)
S      := $(PYTHON) setup.py
M      := make --no-print-directory

default: test

gclean:
	git clean -dfx

fclean:
	- rm -rvf build dist
	- find ./ -type d -name __pycache__ -print0 | xargs -r0 rm -rv
	- find ./ -type f -name \*.pyc      -print0 | xargs -r0 rm -rv
	- find ./ -type d -name \*.egg-info -print0 | xargs -r0 rm -rv

clean:
	@+ if [ -d .git ]; then $(M) gclean; else $(M) fclean; fi

sc super-clean: clean uninstall

ti test-install:
	@+ $(M) uninstall # insure ordering under -j 10
	@+ $(M) install   #   by reinvoking make

uninstall:
	bash ./.uninstall.sh

help:
	$(S) --help-commands

%:
	$(S) $@

.PHONY: crt sc super-clean default # mark phony targets so we don't also fire $(S) $@

lrt:
	./lrunner --config-file /etc/sslf.conf.test -vl debug
