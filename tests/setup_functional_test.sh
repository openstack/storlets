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

# Install Storlets prerequisite
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
sudo mkdir install/storlets/deploy
echo "Copying vars and hosts file to deploy directory"
sudo cp install/storlets/common.yml-sample install/storlets/deploy/common.yml
sudo cp install/storlets/hosts-sample install/storlets/deploy/hosts
sudo chown -R $USER:$USER install/storlets/deploy
sed -i 's/<Set Me!>/127.0.0.1/g' install/storlets/deploy/common.yml
sed -i 's/<Set Me!>/'$USER'/g' install/storlets/deploy/hosts
sed -i '/ansible_ssh_pass/d' install/storlets/deploy/hosts
# If no arguments are supplied, assume we are under jenkins job, and
# we need to edit common.yml to set the appropriate source dir
if [ -z "$1" ]
then
    sed -i 's/~\/storlets/\/home\/'$USER'\/workspace\/gate-storlets-functional\//g' install/storlets/deploy/common.yml
fi

cd install/storlets
echo "Running hosts cluster_check playbook"
ansible-playbook -s -i deploy/hosts cluster_check.yml
echo "Running docker_repository playbook"
ansible-playbook -s -i deploy/hosts docker_repository.yml
echo "Running docker_base_storlet_images playbook"
ansible-playbook -s -i deploy/hosts docker_base_storlet_images.yml
echo "Running docker_storlet_engine_image playbook"
ansible-playbook -s -i deploy/hosts docker_storlet_engine_image.yml
echo "Running hosts storlet_mgmt playbook"
ansible-playbook -s -i deploy/hosts storlet_mgmt.yml
echo "Running hosts fetch_proxy_conf playbook"
ansible-playbook -s -i deploy/hosts fetch_proxy_conf.yml
echo "Running  host_storlet_engine playbook"
ansible-playbook -s -i deploy/hosts host_storlet_engine.yml
sudo chmod -R 777 /opt/ibm
echo "Running create_default_tenant playbook"
ansible-playbook -i deploy/hosts create_default_tenant.yml

cd -
cp cluster_config.json-sample cluster_config.json
sudo chown $USER:$USER cluster_config.json
echo "export OS_USERNAME=swift; export OS_PASSWORD=passw0rd;" >> ~/.bashrc
echo "export OS_TENANT_NAME=service; export OS_AUTH_URL=http://localhost:5000/v2.0" >> ~/.bashrc
