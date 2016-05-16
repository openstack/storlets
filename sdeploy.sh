#! /bin/bash

# This script deploys storlets over existing swift cluster.

# Make sure we have ansible
install/install_ansible.sh

# Prepare the storlets installation
install/storlets/prepare_storlets_install.sh deploy

# Deploy storlets
cd install/storlets
./install_storlets.sh deploy
cd -
