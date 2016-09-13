#!/bin/bash

set -eu
# Invokes the Swift install process that is based on
# https://github.com/Open-I-Beam/swift-install
# with appropriate pre install preparations
# This is a dev oriented Swift installation that
# uses Keystone and a single device for all rings.
# TODO: Move swift ansible scripts pull from here
# to the swift-install module

# The script takes a block device name as an optional parameter
# The device name can be either 'loop0' or any block device under /dev
# that can be formatted and mounted as a Swift device.
# The script assume it 'can sudo'

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 [target] [ip] [device-name]"
    echo "target = host | docker"
    exit
fi

TARGET=$1
if [ "$TARGET" != "host" ] && [ "$TARGET" != "docker" ]; then
    echo "target must be either \"host\" or \"docker\""
    exit 1
fi

SWIFT_IP=$2
DEVICE=$3
if [ $DEVICE != 'loop0' ] &&  [ ! -b "/dev/$DEVICE" ]; then
    echo "$DEVICE is not a block device"
    exit
fi

REPODIR='/tmp'
REPODIR_REPLACE='\/tmp'

echo "$DEVICE will be used as a block device for Swift"
if [ ! -e vars.yml ]; then
    cp vars.yml-sample vars.yml
    sudo sed -i 's/<set device!>/'$DEVICE'/g' vars.yml
    sudo sed -i 's/<set dir!>/'$REPODIR_REPLACE'/g' vars.yml
    sudo sed -i 's/<set ip!>/'$SWIFT_IP'/g' vars.yml
fi

if [ $TARGET == 'docker' ]; then
    cat > hosts <<EOF
[s2aio]
$SWIFT_IP

[s2aio:vars]
ansible_ssh_user=root
EOF
    ssh root@$SWIFT_IP 'if [ ! -f ~/.ssh/id_rsa ]; then ssh-keygen -q -t rsa -f ~/.ssh/id_rsa -N ""; fi'
    ssh root@$SWIFT_IP 'cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys'
else
    cat > hosts <<EOF
    [s2aio]
    $SWIFT_IP
EOF
fi

ansible-playbook -i hosts prepare_swift_install.yml

set +eu
# NOTE: Right now, swift-install/provisioning has some tasks to kill no
# running processes (e.g. swift-init proxy stop for clean environment) and
# it will make a non zero exit code causes gate failure so remove set -eu
# trusting those script. (Hopefully, it could be solved in the script)
if [ $TARGET == 'host' ]; then
    cd $REPODIR/swift-install/provisioning
    ansible-playbook -s -i swift_dynamic_inventory.py main-install.yml
else
    ssh root@$SWIFT_IP "bash -c 'cd /tmp/swift-install/provisioning ; ansible-playbook -s -i swift_dynamic_inventory.py main-install.yml'"
fi
