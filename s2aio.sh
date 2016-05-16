#!/bin/bash
# s2aio install from scratch an all in one swift with the storlet engine.
# s2aio has two flavors:
# 1. Jenkins job installation, for running the funciotal tests.
# 2. Developer instalation.

if [ "$#" -ne 1 ]; then
    echo "Usage: s2aio.sh <flavour>"
    echo "flavour = jenkins | dev"
    exit 1
fi

FLAVOR="$1"
if [ "$FLAVOR" != "jenkins" ] && [ "$FLAVOR" != "dev" ]; then
    echo "flavour must be either \"jenkins\" or \"dev\""
    exit 1
fi

# Make sure hostname is resolvable
grep -q -F ${HOSTNAME} /etc/hosts || sudo sed -i '1i127.0.0.1\t'"$HOSTNAME"'' /etc/hosts

install/install_ansible.sh

# Allow Ansible to ssh locally as the current user without a password
# While at it, take care of host key verification.
# This involves:
# 1. Generate an rsa key for the current user if necessary
if [ ! -f ~/.ssh/id_rsa.pub ];
then
    ssh-keygen -q -t rsa -f ~/.ssh/id_rsa -N ""
fi
# 2. Add the key to the user's authorized keys
grep -s -F ${USER} ~/.ssh/authorized_keys || cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
# 3. Take care of host key verification for the current user
ssh-keygen -R localhost -f ~/.ssh/known_hosts
ssh-keyscan -H localhost >> ~/.ssh/known_hosts
ssh-keyscan -H 127.0.0.1 >> ~/.ssh/known_hosts

# Allow Ansible to ssh locally as root without a password
sudo mkdir -p /root/.ssh
sudo grep -s -F ${USER} /root/.ssh/authorized_keys || sudo sh -c 'cat ~/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys'
sudo sh -c 'echo "" >> /etc/ssh/sshd_config'
sudo sh -c 'echo "# allow ansible connections from local host" >> /etc/ssh/sshd_config'
sudo sh -c 'echo "Match Address 127.0.0.1" >> /etc/ssh/sshd_config'
sudo sh -c 'echo "\tPermitRootLogin without-password" >> /etc/ssh/sshd_config'
sudo service ssh restart

# Install Swift
# TODO: move gcc to swift-installation
sudo apt-get install -y gcc
cd install/swift
./install_swift.sh
cd -

install/storlets/prepare_storlets_install.sh "$FLAVOR"

# Install Storlets
cd install/storlets
./install_storlets.sh "$FLAVOR"
cd -

# TODO: this is for tests. Deal accordingly.
cp install/storlets/deploy/cluster_config.json .
sudo chown $USER:$USER cluster_config.json

echo "export OS_USERNAME=tester; export OS_PASSWORD=testing;" >> ~/.bashrc
echo "export OS_TENANT_NAME=test; export OS_AUTH_URL=http://localhost:5000/v2.0" >> ~/.bashrc
