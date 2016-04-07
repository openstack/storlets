#!/bin/bash

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

function usage() {
    echo "Usage: $0 [device-name]";
}

if [ "$#" -eq 0 ]; then
    DEVICE='loop0'
elif [ "$#" -eq 1 ]; then
    DEVICE=$1
    if [ $DEVICE != 'loop0' ] &&  [ ! -b "/dev/$DEVICE" ]; then
        echo "$DEVICE is not a block device"
        exit
    fi
else
    usage
    exit
fi

REPODIR='\/tmp'

echo "$DEVICE will be used as a block device for Swift"
if [ ! -e vars.yml ]; then
    cp vars.yml-sample vars.yml
    sudo sed -i 's/<set device!>/'$DEVICE'/g' vars.yml
    sudo sed -i 's/<set dir!>/'$REPODIR'/g' vars.yml
fi

ansible-playbook -i hosts prepare_swift_install.yml 

#cd $REPODIR/swift-install/provisioning
#ansible-playbook -s -i swift_dynamic_inventory main-install

