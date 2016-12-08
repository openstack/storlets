#!/bin/bash

set -eu
# Invokes a devstack install that consists of
# keyastone and swift.

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 [target] [ip] [flavour]"
    echo "target = host | docker"
    exit
fi

TARGET=$1
if [ "$TARGET" != "host" ] && [ "$TARGET" != "docker" ]; then
    echo "target must be either \"host\" or \"docker\""
    exit 1
fi

SWIFT_IP=$2

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

DEVSTACK_DIR=~/devstack

# checkout devstack, run it and add fstab entry
if [ ! -e $DEVSTACK_DIR ]; then
    git clone git://github.com/openstack-dev/devstack.git $DEVSTACK_DIR
    cp $DIR/localrc.sample $DEVSTACK_DIR/localrc
    sed -i 's/<set ip!>/'$SWIFT_IP'/g' $DEVSTACK_DIR/localrc
    sed -i 's/<set db password!>/admin/g' $DEVSTACK_DIR/localrc
fi

# run devstack
cd $DEVSTACK_DIR

# This is an ugly hack to overcome
# devstack installation problem in docker
# TODO(eranr): address this after
# adding a devstack plugin to storlets!
if [ "$TARGET" == "docker" ]; then
    set +e
    ./stack.sh
    sudo service mysql start
    set -e
fi
./stack.sh
# stack.sh starts swift in a non-standard manner
# we thus stop it before continuing
set +u
source functions
source lib/swift
stop_swift
set -u
cd -

# add tester, testing, test which is admin
source $DEVSTACK_DIR/localrc
project_test_created=$(openstack project list | grep -w $SWIFT_DEFAULT_PROJECT | wc -l)
if [ $project_test_created -eq 0 ]; then
    openstack project create $SWIFT_DEFAULT_PROJECT
fi
user_tester_created=$(openstack user list | grep -w $SWIFT_DEFAULT_USER | wc -l)
if [ $user_tester_created -eq 0 ]; then
    openstack user create --project $SWIFT_DEFAULT_PROJECT --password $SWIFT_DEFAULT_USER_PWD $SWIFT_DEFAULT_USER
    openstack role add --user $SWIFT_DEFAULT_USER --project $SWIFT_DEFAULT_PROJECT admin
fi

# add entry to fstab
mount_added=$(grep swift.img /etc/fstab | wc -l)
if [ $mount_added -eq 0 ]; then
    sudo sh -c 'echo "/opt/stack/data/swift/drives/images/swift.img /opt/stack/data/swift/drives/sdb1 xfs loop" >> /etc/fstab'
fi

set +eu
