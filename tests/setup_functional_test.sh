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
sudo mkdir Deploy/playbook/deploy
echo "Copying vars and hosts file to deploy directory"
sudo cp Deploy/playbook/common.yml-sample Deploy/playbook/deploy/common.yml
sudo cp Deploy/playbook/hosts-sample Deploy/playbook/deploy/hosts
sudo chown -R $USER:$USER Deploy/playbook/deploy
sed -i 's/<Set Me!>/127.0.0.1/g' Deploy/playbook/deploy/common.yml
sed -i 's/<Set Me!>/'$USER'/g' Deploy/playbook/deploy/hosts
sed -i '/ansible_ssh_pass/d' Deploy/playbook/deploy/hosts
# If no arguments are supplied, assume we are under jenkins job, and
# we need to edit common.yml to set the appropriate source dir
if [ -z "$1" ]
  then
    sed -i 's/~\/storlets/\/home\/'$USER'\/workspace\/gate-storlets-functional\//g' Deploy/playbook/deploy/common.yml
fi

cd Deploy/playbook
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
