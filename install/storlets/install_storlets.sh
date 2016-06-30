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

# echo "Running hosts cluster_check playbook"
ansible-playbook -s -i storlets_dynamic_inventory.py cluster_check.yml

echo "Running hosts docker_cluster playbook"
ansible-playbook -s -i storlets_dynamic_inventory.py docker_cluster.yml

echo "Running the host_side_storlet_engine playbook"
ansible-playbook -s -i storlets_dynamic_inventory.py host_side_storlet_engine.yml

echo "Running the enable_storlets_for_default_tenant playbook"
ansible-playbook -s -i storlets_dynamic_inventory.py enable_storlets_for_default_tenant.yml

# TODO(eranr): Get back to the ant dev playbooks!!!
