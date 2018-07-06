#!/usr/bin/env bash

PY="$(which python)"
PY_BIN="$(dirname "$PY")"
PY_DIR="$(dirname "$PY_BIN")"

echo PY=$PY
echo PY_BIN=$PY_BIN
echo PY_DIR=$PY_DIR
[ -x "$PY_BIN/python" -a -n "$PY_DIR" -a -d "$PY_DIR" ] || exit 1

rm -rvf "$PY_BIN/sslf" "$PY_DIR"/lib/python*/{site-*,dist-*}/{splunk-super-*,SplunkSuper*}
