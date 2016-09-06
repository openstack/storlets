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

if [ "$#" -eq 0 ]; then
    DEVICE='loop0'
elif [ "$#" -eq 1 ]; then
    DEVICE=$1
    if [ $DEVICE != 'loop0' ] &&  [ ! -b "/dev/$DEVICE" ]; then
        echo "$DEVICE is not a block device"
        exit
    fi
else
    echo "Usage: $0 [device-name]";
    exit
fi

REPODIR='/tmp'
REPODIR_REPLACE='\/tmp'

echo "$DEVICE will be used as a block device for Swift"
if [ ! -e vars.yml ]; then
    cp vars.yml-sample vars.yml
    sudo sed -i 's/<set device!>/'$DEVICE'/g' vars.yml
    sudo sed -i 's/<set dir!>/'$REPODIR_REPLACE'/g' vars.yml
fi

ansible-playbook -i hosts prepare_swift_install.yml

set +eu
# NOTE: Right now, swift-install/provisioning has some tasks to kill no
# running processes (e.g. swift-init proxy stop for clean environment) and
# it will make a non zero exit code causes gate failure so remove set -eu
# trusting those script. (Hopefully, it could be solved in the script)
cd $REPODIR/swift-install/provisioning
ansible-playbook -s -i swift_dynamic_inventory.py main-install.yml
