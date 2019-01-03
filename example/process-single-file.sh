#!/bin/bash

rm -rvf /tmp/sslf/meta

# NOTE: other settings come from /etc/sslf.conf

FILE="${1:-${FILE:-/tmp/file.json}}"

./lrunner --path "$FILE:index=tmp,reader=jsonlines" \
    --opt pid_file=/tmp/sslf/pid log_file=/tmp/sslf/log disk_queue=/tmp/sslf/dq \
          meta_data_dir=/tmp/sslf/meta log_level=debug

