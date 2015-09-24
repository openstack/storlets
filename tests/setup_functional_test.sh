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

ssh-keygen -q -t rsa -f /home/jenkins/.ssh/id_rsa -N ""
cp /home/jenkins/.ssh/id_rsa.pub /home/jenkins/.ssh/authorized_keys

ansible-playbook -s -i tests/swift_install/hosts tests/swift_install/swift_install.yml

# install the lxc-docker package
#sudo apt-get update
#sudo apt-get install -y linux-image-extra-`uname -r`
#sudo sh -c "wget -qO- https://get.docker.io/gpg | apt-key add -"
#sudo sh -c "echo deb http://get.docker.io/ubuntu docker main > /etc/apt/sources.list.d/docker.list"
#sudo apt-get update
#sudo apt-get install -y lxc-docker
