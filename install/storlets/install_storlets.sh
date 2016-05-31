if [ ! -d deploy ]; then
    mkdir deploy
fi
cp prepare_vars.yml-sample deploy/prepare_vars.yml
sed -i 's/<ANSIBLE_USER>/'$USER'/g' deploy/prepare_vars.yml
sed -i 's/<MGMT_USER>/'$USER'/g' deploy/prepare_vars.yml
sed -i 's/<SWIFT_RUNTIME_USER>/swift/g' deploy/prepare_vars.yml
sed -i 's/<SWIFT_RUNTIME_GROUP>/swift/g' deploy/prepare_vars.yml
ansible-playbook -i prepare_host prepare_storlets_install.yml

#echo "Copying vars and hosts file to deploy directory"
if [ -z "$1" ]
then
    sed -i 's/~\/storlets/\/home\/'$USER'\/workspace\/gate-storlets-functional\//g' deploy/cluster_config.json
fi

echo "Running hosts cluster_check playbook"
ansible-playbook -s -i storlets_dynamic_inventory.py cluster_check.yml

echo "Running docker_repository playbook"
ansible-playbook -s -i storlets_dynamic_inventory.py docker_repository.yml

echo "Running docker_base_storlet_images playbook"
ansible-playbook -s -i storlets_dynamic_inventory.py docker_base_storlet_images.yml

echo "Running docker_storlet_engine_image playbook"
ansible-playbook -s -i storlets_dynamic_inventory.py docker_storlet_engine_image.yml

echo "Running hosts storlet_mgmt playbook"
ansible-playbook -s -i storlets_dynamic_inventory.py storlet_mgmt.yml

echo "Running hosts fetch_proxy_conf playbook"
ansible-playbook -s -i storlets_dynamic_inventory.py fetch_proxy_conf.yml

echo "Running  host_storlet_engine playbook"
ansible-playbook -s -i storlets_dynamic_inventory.py  host_storlet_engine.yml
sudo chmod -R 777 /opt/ibm

echo "Running create_default_tenant playbook"
#  This assumes the user running the script is also the storlet-mgmt user!
ansible-playbook -i storlets_dynamic_inventory.py create_default_tenant.yml

#ansible-playbook -s -i $1 storlet.yml
