#!/bin/bash

echo 'Copy logs into workspace'

LOG_DIR=$WORKSPACE/logs

if [ `command -v dpkg` ]; then
    sudo dpkg -l > $LOG_DIR/packages.txt
elif [ `command -v rpm` ]; then
    sudo rpm -qa | sort > $LOG_DIR/packages.txt
fi

if [ `command -v docker` ]; then
    sudo docker ps -a > $LOG_DIR/docker_ps_-a.txt
    sudo docker images > $LOG_DIR/docker_images.txt
fi
