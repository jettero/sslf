#!/bin/bash

rm -rvf /tmp/sslf/meta

./lrunner --path /tmp/sslf/blah:index=tmp,reader=jsonlines \
    --opt pid_file=/tmp/sslf/pid log_file=/tmp/sslf/log disk_queue=/tmp/sslf/dq \
          meta_data_dir=/tmp/sslf/meta log_level=debug

