#!/bin/bash

# Make sure hostname is resolvable
grep -q -F ${HOSTNAME} /etc/hosts || sudo sed -i '1i127.0.0.1\t'"$HOSTNAME"'' /etc/hosts

# Install Ansible. Current scripts rely on
# features which are not in ubuntu repo Ansible
sudo apt-get install -y software-properties-common
sudo apt-add-repository -y ppa:ansible/ansible
sudo apt-get update
sudo apt-get install -y ansible

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

# Install Storlets
cd install/storlets
./install_storlets.sh $1
cd -

# TODO: this is for tests. Deal accordingly.
cp cluster_config.json-sample cluster_config.json
sudo chown $USER:$USER cluster_config.json

echo "export OS_USERNAME=swift; export OS_PASSWORD=passw0rd;" >> ~/.bashrc
echo "export OS_TENANT_NAME=service; export OS_AUTH_URL=http://localhost:5000/v2.0" >> ~/.bashrc
