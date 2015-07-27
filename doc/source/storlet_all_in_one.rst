=====
S2AIO
=====
swift-storlets all in one is an Ansible based script that installs both swift and storlets in a virtual machine.
To run the script simply cd to the s2aio directory, edit the credentials for localhost in the hosts file, and run
the *storlets_aio.sh* script. The credentials for localhost must be of a 'sudoer user'
Note that the script takes a long time to run (10 minutes or more). More information below. 

The script does the following:

1. Download the swift-install repo <https://github.com/Open-I-Beam/swift-install> and uses it
   to install swift all in one inside a VM.
2. Download the swift-storlets repo into the VM, and executes the storlets installation within it.

One can edit s2aio/vars.yaml to control various parameters of the installation. Parameters of interest are:

* *installation_dir*. the directory where the swift-install repo is downloaded and where the VM data will reside
* *ip_prefix*. The prefix of the VMs IP
* *installation_user* and *installation_password*. Do not change these as they are aligned with the user created for the provisioned VM. These can be controlled via the swift-install tunables which are beyond the scope of this short doc.

The defaults for the storlets installation are found in:

* s2aio/roles/install_storlets/templates/common.yml
* s2aio/hosts

known issues
------------
1. Most issues are around ssh: The *storlets_aio.sh* script activates 2 major ansible playbooks:

  * An ansible playbook that uses ssh to localhost with root or a 'sudoer user'
  * An ansible palybook that is activated within the VM and uses ssh to localhost (within the VM) with the user vagrant

  Although Ansible is configured not to check the host key, it sometimes fail. If this is the case just ssh manually where required and confirm the host key

2. The script takes a long time to run, and for most of the time it does not show progress. An alternative to executing *storlets_aio.sh* are the following steps. These would allow monitoring the progress of the ansible installation inside the VM.

 1. cd s2aio
 2. export ANSIBLE_HOST_KEY_CHECKING=False
 3. ansible-playbook -s -i swift_install.yml
 4. ansible-playbook -s -i prepare_storlets_install.yml
 5. ssh vagrant 192.168.10.2 (using 'vagrant' as password)

 Now, inside the VM:

 1. cd /home/vagrant/swift-storlets
 2. ant build
 3. cd Deploy/playbook
 4. ansible-playbook -s -i hosts storlet.yml

3. Sometimes the storlet installation part fails on a docker build operation. Usually, re-executing the ansible playbook is enough. This seems to have disappeared with Docker 1.6.2. Leaving the comment for a while.
