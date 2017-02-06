#!/bin/bash
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

set -e

REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DEVSTACK_DIR=~/devstack
SWIFT_IP=127.0.0.1
KEYSTONE_IP=$SWIFT_IP
KEYSTONE_PROTOCOL=http
KEYSTONE_PUBLIC_URL=${KEYSTONE_PROTOCOL}://${KEYSTONE_IP}/identity/v3
IDENTITY_API_VERSION=3

SWIFT_DATA_DIR=/opt/stack/data/swift

usage() {
    echo "Usage: s2aio.sh install"
    echo "       s2aio.sh start"
    echo "       s2aio.sh stop"
    exit 1
}

_prepare_devstack_env() {
    # Checkout devstack
    if [ ! -e $DEVSTACK_DIR ]; then
        git clone git://github.com/openstack-dev/devstack.git $DEVSTACK_DIR
        cp devstack/localrc.sample $DEVSTACK_DIR/localrc
    fi

    source $DEVSTACK_DIR/functions
    source $DEVSTACK_DIR/functions-common
    source $DEVSTACK_DIR/lib/swift
    source devstack/plugin.sh
}

start_s2aio() {
    set -e
    swift-init --run-dir ${SWIFT_DATA_DIR}/run/ all start
    /usr/local/bin/uwsgi /etc/keystone/keystone-uwsgi-public.ini &> /dev/null &
    /usr/local/bin/uwsgi /etc/keystone/keystone-uwsgi-admin.ini &> /dev/null &
    exit 0
}

_stop_s2aio() {
    set +e
    swift-init --run-dir ${SWIFT_DATA_DIR}/run/ all stop
    sh -c 'ps aux | pgrep uwsgi | xargs kill -9'
    set -e
}

stop_s2aio() {
    _stop_s2aio
    exit 0
}

install_swift_using_devstack() {
    cd $DEVSTACK_DIR
    ./stack.sh
    stop_swift
    cd -

    # add entry to fstab
    mount_added=$(grep swift.img /etc/fstab | wc -l)
    if [ $mount_added -eq 0 ]; then
        sudo sh -c 'echo "/opt/stack/data/swift/drives/images/swift.img /opt/stack/data/swift/drives/sdb1 xfs loop" >> /etc/fstab'
    fi
}

install_s2aio() {
    _prepare_devstack_env

    install_swift_using_devstack
    install_storlets

    echo "export OS_IDENTITY_API_VERSION=$KEYSTONE_IDENTITY_API_VERSION" >> ~/.bashrc
    echo "export OS_USERNAME=$SWIFT_DEFAULT_USER; export OS_PASSWORD=$SWIFT_DEFAULT_USER_PWD" >> ~/.bashrc
    echo "export OS_PROJECT_NAME=$SWIFT_DEFAULT_PROJECT; export OS_DEFAULT_DOMAIN=default" >> ~/.bashrc
    echo "export OS_AUTH_URL=$KEYSTONE_PUBLIC_URL" >> ~/.bashrc
}

uninstall_swift_using_devstack() {
    _stop_s2aio
    cd $DEVSTACK_DIR
    ./unstack.sh
    cd -

    echo "Removing swift device mount, creating /etc/fstab.bak"
    sudo sed -i.bak '/swift.img/d'  /etc/fstab
}


uninstall_s2aio() {
    _prepare_devstack_env

    echo "Removing all storlets run time data"
    uninstall_storlets

    echo "Uninstalling Swift"
    uninstall_swift_using_devstack
}

COMMAND="$1"
case $COMMAND in
  "install" )
    install_s2aio
    ;;

  "uninstall" )
    uninstall_s2aio
    ;;

  "start" )
    start_s2aio
    ;;

  "stop" )
    stop_s2aio
    ;;
  * )
    usage
esac

set +e
