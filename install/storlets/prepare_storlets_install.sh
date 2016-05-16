#!/bin/bash

# The storlets installation has 3 flavors:
# 1. Jenkins job installation, for running the funciotal tests.
# 2. Developer instalation.
# 3. Deployment over existing Swift cluster
if [ "$#" -ne 1 ]; then
    echo "Usage: s2aio.sh <flavour>"
    echo "flavour = jenkins | dev | deploy"
    exit 1
fi

FLAVOR="$1"
if [ "$FLAVOR" != "jenkins" ] && [ "$FLAVOR" != "dev" ] && [ "$FLAVOR" != "deploy" ]; then
    echo "flavour must be either \"jenkins\" or \"dev\" or \"deploy\""
    exit 1
fi

# Install Storlets build prerequisite
sudo apt-get install -y ant
sudo add-apt-repository -y ppa:webupd8team/java
sudo apt-get update
sudo echo "oracle-java8-installer shared/accepted-oracle-license-v1-1 select true" | sudo debconf-set-selections
sudo apt-get install --force-yes -y oracle-java8-installer
sudo apt-get install --force-yes -y oracle-java8-set-default
sudo apt-get install -y python
sudo apt-get install -y python-setuptools

# Build Storlets
ant build

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
    sed -i 's/<ANSIBLE_USER>/'$USER'/g' deploy/installation_vars.yml
    sed -i 's/<MGMT_USER>/'$USER'/g' deploy/installation_vars.yml
    sed -i 's/<SWIFT_RUNTIME_USER>/swift/g' deploy/installation_vars.yml
    sed -i 's/<SWIFT_RUNTIME_GROUP>/swift/g' deploy/installation_vars.yml
    if [ "$FLAVOR" == "jenkins" ]; then
        sed -i 's/<STORLETS_REPO_ROOT>/\/home\/'$USER'\/workspace\/gate-storlets-functional\//g' deploy/installation_vars.yml
    else
        sed -i 's/<STORLETS_REPO_ROOT>/~\/storlets\//g' deploy/installation_vars.yml
    fi
    cp prepare_host-sample deploy/prepare_host
    sed -i 's/<PREPARING_HOST>/127.0.0.1/g' deploy/prepare_host
fi

ansible-playbook -s -i deploy/prepare_host prepare_storlets_install.yml

cd -
