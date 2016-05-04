sudo mkdir deploy
echo "Copying vars and hosts file to deploy directory"
sudo cp common.yml-sample deploy/common.yml
sudo cp hosts-sample deploy/hosts
sudo chown -R $USER:$USER deploy
sed -i 's/<Set Me!>/127.0.0.1/g' deploy/common.yml
sed -i 's/<Set Me!>/'$USER'/g' deploy/hosts
sed -i '/ansible_ssh_pass/d' deploy/hosts
# If no arguments are supplied, assume we are under jenkins job, and
# we need to edit common.yml to set the appropriate source dir
if [ -z "$1" ]
then
    sed -i 's/~\/storlets/\/home\/'$USER'\/workspace\/gate-storlets-functional\//g' deploy/common.yml
fi

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

#ansible-playbook -s -i $1 storlet.yml
