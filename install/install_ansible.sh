# Install Ansible. Current scripts rely on
# features which are not in ubuntu repo Ansible
ANSIBLE_EXISTS=1
ansible --version >/dev/null 2>&1 || { ANSIBLE_EXISTS=0; }
if [ "$ANSIBLE_EXISTS" -eq 1 ]
then
    VERSION_LINE=$(ansible --version)
    IFS=' ' read -ra VERSION_TUPLE <<< "$VERSION_LINE" &> /dev/null
    IFS='.' read -ra VERSION <<< "${VERSION_TUPLE[1]}" &> /dev/null
    if [ "${VERSION[0]}" -lt 2 ]
    then
        ANSIBLE_EXISTS=0
    fi
fi

if [ "$ANSIBLE_EXISTS" -eq 0 ]
then
    sudo apt-get install -y software-properties-common
    sudo apt-add-repository -y ppa:ansible/ansible
    sudo apt-get update
    sudo apt-get install -y ansible
fi
