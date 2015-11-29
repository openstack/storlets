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
sudo sed -i 's/<Set Me!>/'$USER'/g' localhost_config.json
ansible-playbook -s -i inventory/vagrant/localhost_dynamic_inventory.py main-install.yml

cd -
sed -i 's/<Set Me!>/127.0.0.1/g' Deploy/playbook/common.yml
sed -i 's/<Set Me!>/'$USER'/g' Deploy/playbook/hosts
sed -i '/ansible_ssh_pass/d' Deploy/playbook/hosts
# If no arguments are supplied, assume we are under jenkins job, and
# we need to edit common.yml to set the appropriate source dir
if [ -z "$1" ]
  then
    sed -i 's/~\/storlets/\/home\/'$USER'\/workspace\/gate-storlets-functional\//g' Deploy/playbook/common.yml
fi

cd Deploy/playbook
ansible-playbook -s -i hosts cluster_check.yml
ansible-playbook -s -i hosts docker_repository.yml
ansible-playbook -s -i hosts docker_base_storlet_images.yml
ansible-playbook -s -i hosts docker_storlet_engine_image.yml
ansible-playbook -s -i hosts storlet_mgmt.yml
ansible-playbook -s -i hosts fetch_proxy_conf.yml
ansible-playbook -s -i hosts host_storlet_engine.yml
sudo chmod -R 777 /opt/ibm
ansible-playbook -i hosts create_default_tenant.yml
