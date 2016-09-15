#!/bin/bash

set -eu
echo "Running hosts cluster_check playbook"
ansible-playbook -s -i storlets_dynamic_inventory.py cluster_check.yml

echo "Running hosts docker_cluster playbook"
ansible-playbook -s -i storlets_dynamic_inventory.py docker_cluster.yml

echo "Running the host_side_storlet_engine playbook"
ansible-playbook -i storlets_dynamic_inventory.py host_side_storlet_engine.yml

echo "Running the enable_storlets_for_default_tenant playbook"
ansible-playbook -i storlets_dynamic_inventory.py enable_storlets_for_default_tenant.yml

# TODO(eranr): Get back to the ant dev playbooks!!!
set +eu
