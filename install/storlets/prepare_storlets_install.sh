#!/bin/bash

# The storlets installation has 3 flavors:
# 1. Jenkins job installation, for running the funciotal tests.
# 2. Developer instalation.
# 3. Deployment over existing Swift cluster
# There are two possible targets:
# 1. host (localhost)
# 2. docker
if [ "$#" -ne 2 ]; then
    echo "Usage: prepare_storlets_install.sh <flavor> <target>"
    echo "flavor = jenkins | dev | deploy"
    echo "target = host | docker"
    exit 1
fi

TARGET="$2"
if [ "$TARGET" != "host" ] && [ "$TARGET" != "docker" ]; then
    echo "target must be either \"host\" or \"docker\""
    exit 1
fi

if [ "$TARGET" == "host" ]; then
    export SWIFT_IP='127.0.0.1'
else
    export SWIFT_IP=`sudo docker exec s2aio ifconfig | grep "inet addr" | head -1 | awk '{print $2}' | awk -F":" '{print $2}'`
fi

FLAVOR="$1"
if [ "$FLAVOR" != "jenkins" ] && [ "$FLAVOR" != "dev" ] && [ "$FLAVOR" != "deploy" ]; then
    echo "flavor must be either \"jenkins\" or \"dev\" or \"deploy\""
    exit 1
fi

# Install Storlets build prerequisite
sudo add-apt-repository -y ppa:openjdk-r/ppa
sudo apt-get update
sudo apt-get install -y openjdk-8-jdk-headless
sudo apt-get install -y ant
sudo apt-get install -y python
sudo apt-get install -y python-setuptools

sudo ./install_libs.sh

# Note(takashi): Currently we need to use tar ball to storelet repo
#                files, to avoid slow perfomance of copy module
#                when dealing with a directory
tar czf /tmp/storlets.tar.gz .

# The rest of the operations are all relative to
# install/storlets/
cd install/storlets

if [ ! -d deploy ]; then
    mkdir deploy
fi

if [ "$FLAVOR" == "deploy" ]; then
    if [ ! -e deploy/installation_vars.yml ]; then
        echo "deploy installation must have deploy/installation_vars.yml in place"
        exit 1
    fi
else
    cp installation_vars.yml-sample deploy/installation_vars.yml
    if [ $TARGET == 'host' ]; then
        sed -i 's/<ANSIBLE_USER>/'$USER'/g' deploy/installation_vars.yml
        sed -i 's/<MGMT_USER>/'$USER'/g' deploy/installation_vars.yml
    else
        sed -i 's/<ANSIBLE_USER>/root/g' deploy/installation_vars.yml
        sed -i 's/<MGMT_USER>/root/g' deploy/installation_vars.yml
        sed -i 's/127.0.0.1/'$SWIFT_IP'/g' deploy/installation_vars.yml
    fi
    sed -i 's/<SWIFT_RUNTIME_USER>/'$USER'/g' deploy/installation_vars.yml
    sed -i 's/<SWIFT_RUNTIME_GROUP>/'$USER'/g' deploy/installation_vars.yml
    sed -i 's/<SWIFT_RUNTIME_DIR>/\/opt\/stack\/data\/swift\/run/g' deploy/installation_vars.yml
    if [ "$FLAVOR" == "jenkins" ]; then
        sed -i 's/<STORLETS_REPO_ROOT>/\/home\/'$USER'\/workspace\/gate-storlets-functional\//g' deploy/installation_vars.yml
    else
        sed -i 's/<STORLETS_REPO_ROOT>/~\/storlets\//g' deploy/installation_vars.yml
    fi
    cp prepare_host-sample deploy/prepare_host
    sed -i 's/<PREPARING_HOST>/'$SWIFT_IP'/g' deploy/prepare_host
fi

ansible-playbook -s -i deploy/prepare_host prepare_storlets_install.yml

cd -
