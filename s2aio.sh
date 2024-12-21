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
set -o xtrace

REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DEVSTACK_DIR=~/devstack
SWIFT_IP=127.0.0.1
KEYSTONE_IP=$SWIFT_IP
KEYSTONE_PROTOCOL=http
KEYSTONE_PUBLIC_URL=${KEYSTONE_PROTOCOL}://${KEYSTONE_IP}/identity/v3

SWIFT_DATA_DIR=/opt/stack/data/swift

function usage {
    echo "Usage: s2aio.sh install"
    echo "       s2aio.sh start"
    echo "       s2aio.sh stop"
    exit 1
}

function _prepare_devstack_env {
    # Checkout devstack
    if [ ! -e $DEVSTACK_DIR ]; then
        git clone https://opendev.org/openstack/devstack.git $DEVSTACK_DIR
        cp devstack/localrc.sample $DEVSTACK_DIR/localrc
    fi

    source $DEVSTACK_DIR/functions
    if [[ -z "$os_PACKAGE" ]]; then
        GetOSVersion
    fi
    source $DEVSTACK_DIR/stackrc
    source $DEVSTACK_DIR/lib/keystone
    source $DEVSTACK_DIR/lib/swift
    source devstack/plugin.sh
}

function start_s2aio {
    set -e
    start_keystone
    start_swift
    exit 0
}

function _stop_s2aio {
    set +e
    stop_keystone
    stop_swift
    set -e
}

function stop_s2aio {
    _stop_s2aio
    exit 0
}

function install_swift_using_devstack {
    cd $DEVSTACK_DIR
    ./stack.sh
    cd -
}

function install_s2aio {
    _prepare_devstack_env

    install_swift_using_devstack
    install_storlets

    echo "export OS_USERNAME=$SWIFT_DEFAULT_USER; export OS_PASSWORD=$SWIFT_DEFAULT_USER_PWD" >> ~/.bashrc
    echo "export OS_PROJECT_NAME=$SWIFT_DEFAULT_PROJECT; export OS_DEFAULT_DOMAIN=default" >> ~/.bashrc
    echo "export OS_AUTH_URL=$KEYSTONE_PUBLIC_URL" >> ~/.bashrc
}

function uninstall_swift_using_devstack {
    _stop_s2aio
    cd $DEVSTACK_DIR
    ./unstack.sh
    cd -
}

function uninstall_s2aio {
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
set +o xtrace
