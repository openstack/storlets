#!/bin/bash
set -eu
# s2aio install from scratch an all in one swift with the storlet engine.
# s2aio has two flavors:
# 1. Jenkins job installation, for running the funciotal tests.
# 2. Developer instalation.

if [ "$#" -ne 2 ]; then
    echo "Usage: s2aio.sh <flavor> <target>"
    echo "flavor = jenkins | dev"
    echo "target = host | docker"
    exit 1
fi

FLAVOR="$1"
if [ "$FLAVOR" != "jenkins" ] && [ "$FLAVOR" != "dev" ]; then
    echo "flavor must be either \"jenkins\" or \"dev\""
    exit 1
fi

TARGET="$2"
if [ "$TARGET" != "host" ] && [ "$TARGET" != "docker" ]; then
    echo "target must be either \"host\" or \"docker\""
    exit 1
fi

# Make sure hostname is resolvable
grep -q -F ${HOSTNAME} /etc/hosts || sudo sed -i '1i127.0.0.1\t'"$HOSTNAME"'' /etc/hosts

install/install_ansible.sh

# Allow Ansible to ssh as the current user without a password
# While at it, take care of host key verification.
# This involves:
# 1. Generate an rsa key for the current user if necessary
if [ ! -f ~/.ssh/id_rsa.pub ]; then
    ssh-keygen -q -t rsa -f ~/.ssh/id_rsa -N ""
fi

if [ "$TARGET" == "docker" ]; then
    # install docker
    sudo apt-get install apt-transport-https aufs-tools=1:3.2+20130722-1.1 linux-image-extra-`uname -r` -y --force-yes
    sudo apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
    sudo sh -c "echo deb https://apt.dockerproject.org/repo ubuntu-trusty main > /etc/apt/sources.list.d/docker.list"
    sudo apt-get update
    sudo apt-get install docker-engine -y --force-yes
    sudo sh -c "echo DOCKER_OPTS=\"--storage-driver=vfs\" >> /etc/default/docker"
    sudo service docker restart

    # run the swift docker container
    S2AIO_RUNNING=`sudo docker ps | grep s2aio | wc -l`
    S2AIO_EXISTS=`sudo docker ps -a | grep s2aio | wc -l`
    if [ "$S2AIO_RUNNING" == "0" ]; then
        if [ "$S2AIO_EXISTS" == "1" ]; then
             sudo docker rm s2aio
        fi
        sudo docker run -i -d --privileged=true --name s2aio -t ubuntu:14.04
    fi
    export S2AIO_IP=`sudo docker exec s2aio ifconfig | grep "inet addr" | head -1 | awk '{print $2}' | awk -F":" '{print $2}'`

    sudo docker exec s2aio sh -c "echo deb http://us.archive.ubuntu.com/ubuntu/ trusty-backports main restricted universe multiverse >> /etc/apt/sources.list"
    sudo docker exec s2aio apt-get update
    sudo docker exec s2aio apt-get install software-properties-common -y --force-yes
    sudo docker exec s2aio apt-add-repository -y ppa:ansible/ansible
    sudo docker exec s2aio apt-get update
    sudo docker exec s2aio apt-get install openssh-server git ansible -y --force-yes
    sudo docker exec s2aio service ssh start

    # Add the key to the user's authorized keys
    sudo docker exec s2aio mkdir -p /root/.ssh
    sudo docker exec s2aio bash -c "echo `cat ~/.ssh/id_rsa.pub` > /root/.ssh/authorized_keys"

    # Take care of host key verification for the current user
    touch ~/.ssh/known_hosts
    ssh-keygen -R $S2AIO_IP -f ~/.ssh/known_hosts
    ssh-keyscan  -H $S2AIO_IP >> ~/.ssh/known_hosts

    sudo docker exec s2aio useradd stack
    sudo docker exec s2aio mkdir /home/stack
    sudo docker exec s2aio bash -c 'grep -q "^#includedir.*/etc/sudoers.d" /etc/sudoers ||\
                                    echo "#includedir /etc/sudoers.d" >> /etc/sudoers'
    sudo docker exec s2aio bash -c '( umask 226 && echo "stack ALL=(ALL) NOPASSWD:ALL" >\
                                      /etc/sudoers.d/50_stack_sh )'
    sudo docker cp install/swift/install_swift.sh s2aio:/home/stack/install_swift.sh
    sudo docker cp install/swift/localrc.sample s2aio:/home/stack/localrc.sample
    sudo docker exec s2aio chown -R stack:stack /home/stack
    sudo docker exec --user stack s2aio chmod -R 0755 /home/stack
    sudo docker exec --user stack s2aio /home/stack/install_swift.sh docker $S2AIO_IP
    sudo docker exec s2aio service rsyslog restart
else
    export S2AIO_IP='127.0.0.1'

    # Add the key to the user's authorized keys
    grep -s -F ${USER} ~/.ssh/authorized_keys || cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys

    # Take care of host key verification for the current user
    if [ -f ~/.ssh/known_hosts ]; then
        ssh-keygen -R localhost -f ~/.ssh/known_hosts
    fi
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
    cd install/swift
    ./install_swift.sh host $S2AIO_IP
    cd -
fi

install/storlets/prepare_storlets_install.sh "$FLAVOR" "$TARGET"

# Install Storlets
cd install/storlets
./install_storlets.sh
cd -

# TODO: this is for tests. Deal accordingly.
cp install/storlets/deploy/cluster_config.json .
sudo chown $USER:$USER cluster_config.json

echo "export OS_USERNAME=tester; export OS_PASSWORD=testing;" >> ~/.bashrc
echo "export OS_TENANT_NAME=test; export OS_AUTH_URL=http://"$S2AIO_IP":5000/v2.0" >> ~/.bashrc
set +eu
