============
Introduction
============

The Storlet manager operations currently include:

#. Creating a Storlet enabled tenant.
#. Deploying an image that was created by the tenant admin as described in <https://github.com/openstack/storlets/blob/master/doc/source/archive/building_and_deploying_docker_images.rst>

The scripts providing these operations are located under /opt/ibm in the storlet management machine.

Creating a Storlet enabled Tenant
=================================
The operation of creating a Storlet enabled tenant is made of the following steps:

#. Create a new tenant in Keystone, together with a tenant admin user.
#. Enable the corresponding Swift account for storlets, including the creation of the Storlet specific containers
   whose default names are: storlet, dependency, storletlog and  docker_images
#. Upload the default Storlets image to the account's docker_images container.

Running the creation task
~~~~~~~~~~~~~~~~~~~~~~~~~
The add_new_tenant.py script perform all of the above operations.
Underneath the script uses Ansible.
The script takes 3 parameters:

#. The tenant name to create
#. The user name for the account manager
#. The password for the account manager

Note that the script is aware of the Keystone admin credentials as they
were provided to the initial installation script as described in <https://github.com/openstack/storlets/blob/master/doc/source/installation.rst>

Below is a sample invocation:

::

  root@lnx-ccs8:/opt/ibm# ./add_new_tenant.py
  ./add_new_tenant.py <tenant_name> <user_name> <user_password>
  root@lnx-ccs8:/opt/ibm# ./add_new_tenant.py new_tenant new_tenant_admin passw0rd

  PLAY [localhost] **************************************************************

  GATHERING FACTS ***************************************************************
  ok: [localhost]

  TASK: [get_hosts_object | get hosts object] ***********************************
  changed: [localhost]

  PLAY RECAP ********************************************************************
  localhost                  : ok=2    changed=1    unreachable=0    failed=0   

  PLAY [storlet-mgmt] ***********************************************************

  GATHERING FACTS ***************************************************************
  ok: [localhost]

  TASK: [add_new_tenant | create new tenant new_tenant] *************************
  changed: [localhost]

  TASK: [add_new_tenant | create new user new_tenant_admin for tenant new_tenant] ***
  changed: [localhost]

  TASK: [add_new_tenant | apply role admin to user new_tenant_admin] ************
  changed: [localhost]

  TASK: [add_new_tenant | Set account metadata in swift -- enable storlets] *****
  changed: [localhost]

  TASK: [add_new_tenant | put account container log] ****************************
  changed: [localhost]

  TASK: [add_new_tenant | put account container storlet] ************************
  changed: [localhost]

  TASK: [add_new_tenant | put account container dependency] *********************
  changed: [localhost]

  TASK: [add_new_tenant | put account container docker_images] ******************
  changed: [localhost]

  TASK: [add_new_tenant | save default storlet docker image as tar file] ********
  changed: [localhost]

  TASK: [add_new_tenant | upload docker image to docker_images container] *******
  changed: [localhost]

  TASK: [add_new_tenant | remove storlet docker image tar file] *****************
  changed: [localhost]

  PLAY RECAP ********************************************************************
  localhost                  : ok=12   changed=11   unreachable=0    failed=0   

Deploying a Tenant Image
========================
Recall that in the Docker image build (described in <https://github.com/openstack/storlets/blob/master/doc/source/archive/building_and_deploying_docker_images.rst>) the image was given a name
(specified after -t in the docker build command) and was uploaded as a .tar file to the tenant's docker_images Swift container.
When deploying an image, the Storlet's admin needs to provide the tenant name, the .tar object name and the image name.

Running the deployment task
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Following the example from the build image instructions, the image name is called service_tenant_image
and the object name that was uploaded is service_tenant_image.tar, and so we execute:

::

  root@lnx-ccs8:/opt/ibm# ./deploy_image.py
  ./deploy_image.py <tenant_name> <tar_object_name> <tenant_image_name>
  root@lnx-ccs8:/opt/ibm# ./deploy_image.py new_tenant service_tenant_image.tar service_tenant_image

  PLAY [localhost] **************************************************************

  GATHERING FACTS ***************************************************************
  ok: [localhost]
  
  TASK: [get_hosts_object | get hosts object] ***********************************
  changed: [localhost]
  
  PLAY RECAP ********************************************************************
  localhost                  : ok=2    changed=1    unreachable=0    failed=0   
  
  PLAY [storlet-mgmt] ***********************************************************
  
  GATHERING FACTS ***************************************************************
  ok: [localhost]
  
  TASK: [push_tenant_image | Get the tenant id from Keystone] *******************
  changed: [localhost]
  
  TASK: [push_tenant_image | get image tar file] ********************************
  changed: [localhost]
  
  TASK: [push_tenant_image | load image to local docker registry] ***************
  changed: [localhost]
  
  TASK: [push_tenant_image | create the tenant specific docker image step 1 - create repo dir] ***
  changed: [localhost]
  
  TASK: [push_tenant_image | create the tenant specific docker image step 2 - create Docker file] ***
  changed: [localhost]
  
  TASK: [push_tenant_image | create the tenant specific docker image step 3 - copy tenant_id file to build dir] ***
  changed: [localhost]
  
  TASK: [push_tenant_image | Build the image {{tenant_id.stdout_lines[0]}}] *****
  changed: [localhost]
  
  TASK: [push_tenant_image | Push the image to the global registry] *************
  changed: [localhost]
  
  TASK: [push_tenant_image | remove storlet docker image tar file] **************
  changed: [localhost]
  
  PLAY RECAP ********************************************************************
  localhost                  : ok=10   changed=9    unreachable=0    failed=0   
  
  PLAY [storlet] ****************************************************************
  
  GATHERING FACTS ***************************************************************
  ok: [localhost]
  
  TASK: [pull_tenant_image | Get the tenant id from Keystone] *******************
  changed: [localhost]
  
  TASK: [pull_tenant_image | docker pull] ***************************************
  changed: [localhost]
  
  PLAY RECAP ********************************************************************
  localhost                  : ok=3    changed=2    unreachable=0    failed=0
  
   
  Testing the deployment
  
  Once deployed, all swift nodes should have the image. A docker images command should show a newly created image having a name of the form <repository>:<port>/<tenant keystone id> as shown below.
  
  root@lnx-ccs8:/opt/ibm# docker images
  REPOSITORY                                        TAG                 IMAGE ID            CREATED             VIRTUAL SIZE
  localhost:5001/e0d4204e4e7c4c079a58f0b8156a921b   latest              138e3c6a0b07        3 minutes ago       596.8 MB
  
