=================================================
Deploying storlets over an existing Swift cluster
=================================================
This guide describes how to install the storlet engine over an existing Swift with Keystone
cluster. This guide follows an example where the Swift cluster has one proxy and 3 object nodes.
In addition the guide assume a management machine form which the installation takes place.
The management machine in the example also acts as a Keystone server as well as a Docker
repository for the Docker images created during the deployment.


------------------------
The installation process
------------------------
We bring here the installation process high level steps so as to make
more sense of the various installation configuration parameters described
below. Feel free to skip if you wish to get on with the installation.

- Install a private Docker registry. This is where the various Docker
  images are kept before being deployed across the cluster.
- Building the Docker image for running storlets. The process starts with
  a generic image containing Java and the storlets stuff, and proceeds
  with creating an image for a default tenant over which the tests can
  be executed.
- Deploy the storlet engine python code that runs within Swift, including
  swift configuration changes to incorporate the storlets middleware.
- Create a default tenant that is enabled for storlets.
- Install the storlets management code on the management host. This code
  allows to create new tenants that can use storlets as well as deploy
  Docker images. The installation of this code requires Keystone credentials
  for the creation of a storlet management swift account that keeps the cluster
  configuration.


-----------------------------
The assumed Swift cluster IPs
-----------------------------

The guide uses the following addresses:

::

    management / keystone / docker repository:  192.168.56.200
    proxy                   192.168.56.210
    object1                 192.168.56.220
    object2                 192.168.56.230
    object3                 192.168.56.240

.. note::
  The Ansible installation scripts used throughout the deployment assume that the user root
  can ssh from the management machine all other machines without a password. This includes
  root ssh from the machine to itself, either through 127.0.0.1 or the management address
  (192.168.56.200) in our example

-----------------------------
Clone the storlets repository
-----------------------------
To clone the storlets repository use:

::

    sudo apt-get install git
    git clone https://github.com/openstack/storlets.git

.. note::
  The rest of this guide assumes that everything is
  being executed as root. Specifically, it assumes that
  the checkout is done under /root

--------------------------------
Create the preperation host file
--------------------------------
Create the file '/install/storlets/deploy/prepare_host'
and make sure that the address appearing there
is the addressed configured for root passwordless
ssh to the machine itself. e.g.

::

  [s2aio]
  192.168.56.200

------------------------------------------
Create the installation configuration file
------------------------------------------
Create the file 'install/storlets/deploy/installation_vars.yml'
with the following variables definitions. The below reflects our
deployment example.

::

    ansible_ssh_user: root
    repo_root: /root/storlets/
    mgmt_group: [ "192.168.56.200" ]
    proxy_group: [ "192.168.56.210" ]
    storage_group: [ "192.168.56.220", "192.168.56.230", "192.168.56.240" ]
    docker_group: [ "192.168.56.200" ]
    storlets_management_user: root
    storlet_management_account: "storlet_management"
    storlet_management_admin_username: "storlet_manager"
    storlet_manager_admin_password: "storlet_manager"
    storlets_default_tenant_name: "test"
    storlets_default_tenant_user_name: "tester"
    storlets_default_tenant_user_password: "testing"
    keystone_endpoint_host: 192.168.56.200
    keystone_admin_user: admin
    keystone_admin_password: admin
    keystone_admin_project: admin
    keystone_default_domain: default
    swift_endpoint_host: 192.168.56.210
    swift_endpoint_port: 80
    swift_run_time_user: swift
    swift_run_time_group: swift
    docker_device: /srv/node/sdb

This file is used for creating the cluster_config.json which is
used by the Ansible installation. We give a full description of
the file below.

------------------------
Running the installation
------------------------

If no further tuning is required above the definitiones in
'install/storlets/deploy/installation_vars.yml'
then just run 'sdeploy.sh' from the repository root.

..note::

  You must run sdeploy.sh as root.

If further tuning is required, edit 'sdeploy.sh', remark out the last line:
'install/storlets/install_storlets.sh' deploy and execute the script.
Once it is done, edit 'install/storlets/deploy/cluster_config.json' as required
and then run 'install/storlets/install_storlets.sh' from the repository root

We give below all the variables used in the installation, as they appear
in 'install/storlets/deploy/cluster_config.json'

Cluster config
==============
Below is the full set of variables being used by the storlets installation.
Please refer to the installation instructions below for controlling variables
that do not appear in the above configurable installation_vars.yml

.. note::
  The variables that are controlled using the above installation_vars.yml
  appear below within double curly braces.

::

  {
      "groups" : {
          "storlet-mgmt": [ "192.168.56.200" ],
          "storlet-proxy": [ "192.168.56.210" ],
          "storlet-storage": [ "192.168.56.220", "192.168.56.230", "192.168.56.240" ],
          "docker": [ "192.168.56.200" ]
      },
      "all" : {
          "docker_device": "{{ docker_device }}",
          "storlet_source_dir": "~/storlets",
          "python_dist_packages_dir": "usr/local/lib/python2.7/dist-packages",
          "storlet_gateway_conf_file": "/etc/swift/storlet_docker_gateway.conf",
          "keystone_endpoint_host": "{{ keystone_endpoint_host }}",
          "keystone_public_url": "http://{{ keystone_endpoint_host }}:5000/v3",
          "keystone_admin_password": "{{ keystone_admin_password }}",
          "keystone_admin_user": "{{keystone_admin_user}}",
          "keystone_admin_project": "{{keystone_admin_project}}",
          "keystone_default_domain": "{{keystone_default_domain}}",
          "swift_endpoint_host": "{{ swift_endpoint_host }}",
          "swift_public_url": "http://{{ swift_endpoint_host }}:{{ swift_endpoint_port }}/v1",
          "swift_run_time_user" : "{{ swift_run_time_user }}",
          "swift_run_time_group" : "{{ swift_run_time_group }}",
          "swift_run_time_dir": "{{ swift_run_time_dir }}",
          "storlets_management_user": "{{ storlets_management_user }}",
          "storlet_management_account": "{{ storlet_management_account }}",
          "storlet_management_admin_username": "{{ storlet_management_admin_username }}",
          "storlet_manager_admin_password": "{{ storlet_manager_admin_password }}",
          "storlet_management_swift_topology_container": "swift_cluster",
          "storlet_management_swift_topology_object": "cluster_config.json",
          "storlet_management_ansible_dir": "/opt/ibm/ansible/playbook",
          "storlet_management_install_dir": "/opt/ibm",
          "storlets_enabled_attribute_name": "storlet-enabled",
          "docker_registry_random_string": "ABCDEFGHIJABCDEFGHIJABCDEFGHIJABCDEFGHIJABCDEFGHIJABCDEFGHIJ1234",
          "docker_registry_port": "5001",
          "container_install_dir": "/opt/storlets",
          "base_image_maintainer": "root",
          "base_os_image": "ubuntu_14.04",
          "storlets_image_name_suffix": "ubuntu_14.04_jre8_storlets",
          "swift_user_id": "1003",
          "swift_group_id": "1003",
          "storlets_default_project_name": "{{ storlets_default_tenant_name }}",
          "storlets_default_project_user_name": "{{ storlets_default_tenant_user_name }}",
          "storlets_default_project_user_password": "{{ storlets_default_tenant_user_password }}",
          "storlets_default_project_member_user" : "tester_member",
          "storlets_default_project_member_password" : "member",
          "storlet_middleware": "storlet_handler",
          "storlet_container": "storlet",
          "storlet_dependency": "dependency",
          "storlet_log": "storletlog",
          "storlet_images": "docker_images",
          "storlet_timeout": "40",
          "storlet_gateway_module": "docker",
          "storlet_execute_on_proxy_only": "false",
          "restart_linux_container_timeout": "3"
      }
  }

- The "groups" entry is a standard Ansible entry for the hosts taking part in the installation.
  As mentioned, in our example we have a management host, acting as a docker repository host,
  as well as a proxy and 3 object hosts. The IPs in each group represent management IPs through
  which root can ssh.
- For each IP in the group entry, we have an entry that specifies the user Ansible will use to ssh to
  that IP. In this guide we use root, and assume that a paswordless ssh has been set up for root to ssh
  to all hosts from the management host.
- The "all" entry lists all the variables Ansible uses in the installation:

  - "lxc-device". A directory within each swift host (proxy or storage) where the storlet run time stuff is to be
    placed. This includes the docker images, the storlets code being downloaded locally, the storlets logs, etc.
    It might be a good idea to dedicate a device for this. Note that all hosts must use the same location.
    The value of this entry is an Ansible variable, which is specified in 'install/storlets/deploy/installation_vars.yml'
  - "storlet_source_dir". A full path of the directory where the storlets repository is checked out.
  - "python_dist_packages_dir". The destination where to install the storlet generated python packages. This serves
    both for the host side code as well as the container side code.
  - "storlet_gateway_conf_file". The location where the storlet gateway plugin configuration file is to be placed.
  - Keystone related variables:

    - "keystone_endpoint_host": The host where keystone is installed. The value of this entry is an Ansible variable,
      which is specified in 'install/storlets/deploy/installation_vars.yml'
    - "keystone_public_url": The Keystone public url. This entry makes use of the keystone endpoint host defined above.
    - "keystone_admin_user": The Keystone administration user
    - "keystone_admin_password": Currently not used. Serves for future alternative to the token.

  - Swift related variables:

    - "swift_endpoint_host". The proxy host. The value of this entry is an Ansible variable,
      which is specified in 'install/storlets/deploy/installation_vars.yml'
    - "swift_public_url". The Swift public url. This entry makes use of the swift endpoint host defined above.
    - "swift_run_time_user", "swift_run_time_group". The user and group under which Swift runs. The value of these entries is an
      Ansible variable, which is specified in 'install/storlets/deploy/installation_vars.yml'

  - Storlet management related variables:

   - "storlets_management_user". The management code makes use of Ansible. The user specified here is the user that
     ansible would use to ssh to the various hosts when activated from the management code.. The value of this entry is an
      Ansible variable, which is specified in 'install/storlets/deploy/installation_vars.yml'
   - "storlet_management_account". The Swift account used by the storlet manager.
   - "storlet_management_admin_username", "storlet_manager_admin_password". The Swift credentials of the user that acts as the
     storlet engine manager.
   - "storlet_management_swift_topology_container", "storlet_management_swift_topology_object". The Swift path were the cluster config is kept in Swift.
   - "storlet_management_ansible_dir", "storlet_management_install_dir". The directories where to place the storlet engine management code and the
     Ansible playbooks.

  - Docker private registry variables:

   - "docker_registry_random_string". A random string required by the registry installation.
   - "docker_registry_port". The port the registry daemon listens on. Note that this is different form
     the default port which is used by Keystone.

  - Docker images variables

    - "container_install_dir". This is the directory where all the non-python storlets stuff is installed within
      the container. This must be a full path (starting with a '/') that does not end with a '/'.
    - "base_image_maintainer". The maintainer of the docker images. Note that the user specified is a user withing
      the Lunix container user namespace.
    - "base_os_image". The base OS image used for the Docker images. Serves as a prefix for the generic images created
      by the process.
    - "storlets_image_name_suffix". The suffix used for the base image that containes the storlets stuff.
    - "swift_user_id", "swift_group_id". The user and group id of a Docker container user that is used to run the storlets daemons.

  - The default swift project parameters created by the installation process:

   - "storlets_default_project_name", "storlets_default_project_user_name", "storlets_default_project_user_password"

  - The config paramaters of the storlet middleware:

    - "storlet_middleware". The name of the storlet middleware to appear in the swift config files.
    - "storlet_container". The name of the container where storlets are uploaded to.
    - "storlet_dependency". The name of the container where dependencies are uploaded to.
    - "storlet_log". Curently not in use. Placeholder for future log upload feature.
    - "storlet_images". The name of the container for uploading user tailored images.
    - "storlet_gateway_module". The class implementing the storlets plugin used. Currently, we have only one
      such plugin.
    - "storlet_execute_on_proxy_only". Controls whether storlets will run only on the proxy servers.

  - The config parameters of the storlet gateway plugin

    - "storlet_timeout". The time Swift gives the a storlet to start producung output.
    - "restart_linux_container_timeout": The number of times the middleware tries to spwans a Docker container
      before giving up.
