#!/bin/bash

sudo apt-get install -y ant
sudo apt-get install -y gcc

sudo apt-get install -y software-properties-common
sudo apt-add-repository -y ppa:ansible/ansible
sudo apt-get update
sudo apt-get install -y ansible

sudo add-apt-repository -y ppa:webupd8team/java
sudo apt-get update
sudo echo "oracle-java8-installer shared/accepted-oracle-license-v1-1 select true" | sudo debconf-set-selections
sudo apt-get install -y oracle-java8-installer
sudo apt-get install -y oracle-java8-set-default
sudo apt-get install -y python
sudo apt-get install -y python-setuptools

ant build

ssh-keygen -q -t rsa -f /home/$USER/.ssh/id_rsa -N ""
cp /home/$USER/.ssh/id_rsa.pub /home/$USER/.ssh/authorized_keys

ansible-playbook -s -i tests/swift_install/hosts tests/swift_install/swift_install.yml

cd /tmp/swift_install/swift-install
ansible-playbook -s -i inventory/vagrant/localhost_dynamic_inventory.py main-install.yml

