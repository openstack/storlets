Storlets Installation
=====================

Background
----------

Storlets installation (and build) assume an existing Swift cluster that works with Keystone.
The installation consists of the following components:

#. A set of scripts to assist the Storlets admin. This admin represents the provider, and is responsible for the Storlet enabled accounts and their image management.
   Those scripts make use of a private Docker registry as well as a designated account and containers used to keep Storlet management related state.
#. A Docker engine that is installed on all proxy and object nodes.
#. The Swift storlet middleware and gateway that are installed on all proxy and object nodes.
#. A basic storlets enabled Docker image that is added to the private Docker registry.
#. A default account, enabled for Storlets with a default image deployed on all proxy and object nodes. This image is based on the basic storlets enabled image.

The installation scripts take two input files:

#. A 'hosts' file describing the nodes on which the installation takes place. This is a standard Ansible hosts file that needs to have the following sections (an example is given below).

   #. docker. The node to be installed with a private Docker registry
   #. storlet-mgmt. The node to be installed with the Storlet management scripts
   #. storlet-proxy. The list of the Swift cluster proxies
   #. storlet-storage. The list of the Swift cluster object servers
   #. root or a sudoer credentials Ansible can use to ssh the machines. In the below example we assume all nodes have the same credentials.

#. An Ansible var file with various inputs, such as the Keystone IP and credentials, the Storlet management account information, etc. The file is located in install/storlets/common.yml, and we give below the entries of interest that may need editing.

At a high level the installation consists of the following steps:

#. Install Docker on all nodes.
#. Install the storlets middleware on each of the Swift nodes (proxies and storage nodes).
#. Create a tenant enabled for storlets (assumes Keystone).
#. Deploy a default Docker image for the above tenant.
#. Install a set of storlets management scripts. Done on a designated node having a storlet management role.

hosts file example
------------------

::

  192.168.33.2 ansible_ssh_user=root ansible_ssh_pass=passw0rd
  192.168.33.3 ansible_ssh_user=root ansible_ssh_pass=passw0rd
  192.168.33.4 ansible_ssh_user=root ansible_ssh_pass=passw0rd
  192.168.33.5 ansible_ssh_user=root ansible_ssh_pass=passw0rd

  [docker]
  192.168.33.5

  [storlet-mgmt]
  192.168.33.5

  [storlet-proxy]
  192.168.33.2

  [storlet-storage]
  192.168.33.3
  192.168.33.4

Few notes:

#. For an 'all-in-one' type of installation, one can specify 127.0.0.1 in all sections.
#. If all hosts have the same ssh user and password one can use ansible's group_vars/all
#. Currently, keystoneclient should be installed in all swift nodes, but this limitation will be addressed in the future.
#. It is recommended that the memcache servers on the proxy servers would be accessible from the storage nodes.

common.yml
----------
Below are the entries of interest of common.yml

Special attention should be given to the swift user and group IDs. Make sure they are identical on all hosts and match what is defined in the common.yml file.
The entry 'storlet_execute_on_proxy_only' controls whether storlets will be invoked only on proxy servers or also on object servers. This option allows to use
storlets with EC and encryption. Valid values are true / false

::

  # A cross nodes directory for Storlets internal usage. Must exist with the same name in all proxy and storage nodes.
  docker_device: /home/docker_device

  # A pointer to this repo
  storlet_source_dir: <need to point to the repo root>

  # Swift Access information. The below IP should be an IP of one of the proxies.
  swift_endpoint_host: 127.0.0.1
  swift_public_url: http://{{ swift_endpoint_host }}:80/v1

  # Keystone access information
  keystone_endpoint_host: 127.0.0.1
  keystone_admin_url: http://{{ keystone_endpoint_host }}:35357/v3
  keystone_public_url: http://{{ keystone_endpoint_host }}/identity/v3
  keystone_admin_token: ADMIN
  keystone_admin_password: passw0rd

  # Information for creating an account for the Storlet manager
  storlet_management_account: storlet_management
  storlet_management_admin_username: storlet_manager
  storlet_manager_admin_password: storlet_manager

  # Information for creating a Storlet enabled account
  storlets_default_project_name: test
  storlets_default_project_user_name: tester
  storlets_default_project_user_password: testing

  swift_user_id: 1003
  swift_group_id: 1003

  # middleware and gateway config file constants
  storlet_execute_on_proxy_only: false

Install
-------
To perform the installation follow these steps:

#. Create a hosts file as described above
#. Edit the file install/storlets/common.yml according to the above
#. Under the root dir of the repo run 'ant build'
#. Under install/storlets run 'ansible-playbook -i <hosts file> storlet.yml'
   in case the hosts file has credentials of a sudoer user, you will need to run:  'ansible-playbook -s -i <hosts file> storlet.yml'

Tip: you might want to "export ANSIBLE_HOST_KEY_CHECKING=False" before running the playbook in case the hosts are not in known_hosts.
Note: The hosts file used for running the playbook is also used by the admin tool to deploy future images. Thus, the ssh information kept in
this file must also apply when used from the storlet-mgmt node.
