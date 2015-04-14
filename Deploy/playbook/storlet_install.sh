export export ANSIBLE_HOST_KEY_CHECKING=False
ansible-playbook -s -i $1 storlet.yml
