#!/bin/bash

rm -rvf /tmp/sslf/meta

# NOTE: other settings come from /etc/sslf.conf

FILE="${1:-${FILE:-/tmp/file.json}}"
STYPE="${2:-${STYPE:-single}}"
INDEX="${3:-${INDEX:-tmp}}"

./lrunner --path "$FILE:index=$INDEX,reader=jsonlines,sourcetype=$STYPE" \
    --opt pid_file=/tmp/sslf/pid log_file=/tmp/sslf/log disk_queue=/tmp/sslf/dq \
          meta_data_dir=/tmp/sslf/meta log_level=debug one_step=true

