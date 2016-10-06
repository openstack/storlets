Installing a Development Environment
====================================
This guide gives a step by step installation instructions that are simpler
then what the s2aio.sh script does (e.g. it does not involve a docker registry
installation and configuration). Performing those instructions, as oppose to
just running s2aio.sh, can help in better inderstanding the overall system.

The guide assumes that you already have installed SAIO as described
in http://docs.openstack.org/developer/swift/development_saio.html
It further assumes that you used a partition for storage that is
mounted on /mnt/sdb1, and that the proxy port is 8080.

.. note::

    This guide assumes that the user executing these instructions
    is the same user who installed SAIO. Specifically, it assumes
    that $USER would evaluate to the same user who instslled SAIO.

This process has been tested on Ubuntu 14.04 using Swift 2.7.0.

.. note::

    Completing the  SAIO installation on Ubuntu 14.04 requires an newer version of pip, setuptools and pbr.
    To upgrade pip see
    http://unix.stackexchange.com/questions/36710/how-can-i-upgrade-pip-on-ubuntu-10-04
    To upgrade setuptools and pbr just do:
    pip install --upgrade pbr
    pip install --upgrade setuptools

Make Swift use Keystone
=======================

SAIO uses tmpauth as an auth middleware. While storlets do not have a
direct dependency on the auth middleware used, Keystone seems to be
the de-facto standard in deployments, and so we use it.

Keystone Installation
---------------------
Below we use the ubuntu mitaka cloud archive.
As a rule of thumb, use the archive closest to the
installed SAIO version

::

    sudo apt-get install --upgrade software-properties-common
    sudo add-apt-repository cloud-archive:mitaka
    sudo apt-get update
    sudo apt-get install keystone
    sudo sed -i 's/#admin_token = <None>/admin_token = ADMIN/g' /etc/keystone/keystone.conf
    sudo service keystone restart

To configure Keystone you would also need to:

::

    sudo apt-get install python-openstackclient


Initial Keystone Configutation
------------------------------
The following creates the identity and object store service together with their endpoints.
Note the usage of port 8080 in the object store public url. If your SAIO uses another port
change the below command accordingly.

::

    openstack --os-token ADMIN --os-url http://127.0.0.1:35357/v2.0/ service create identity
    openstack --os-token ADMIN --os-url http://127.0.0.1:35357/v2.0/ endpoint create --publicurl http://127.0.0.1:5000/v2.0 --adminurl http://127.0.0.1:35357/v2.0 identity
    openstack --os-token ADMIN --os-url http://127.0.0.1:35357/v2.0/ service create object-store
    openstack --os-url http://127.0.0.1:35357/v2.0/ --os-token ADMIN endpoint create --publicurl 'http://127.0.0.1:8080/v1/AUTH_$(tenant_id)s' object-store

Create a Swift admin user. The Swift proxy will use this user to authorize tokens with Keystone

::

    openstack --os-token ADMIN --os-url http://127.0.0.1:35357/v2.0/ role create admin
    openstack --os-token ADMIN --os-url http://127.0.0.1:35357/v2.0/ project create service
    openstack --os-token ADMIN --os-url http://127.0.0.1:35357/v2.0/ user create swift --password passw0rd
    openstack --os-token ADMIN --os-url http://127.0.0.1:35357/v2.0/ role add --user swift --project service admin

Create a Swift end user that is admin. The admin role is necessary as we want a user that can create containers and set account metadata

::

    openstack --os-token ADMIN --os-url http://127.0.0.1:35357/v2.0/ project create test
    openstack --os-token ADMIN --os-url http://127.0.0.1:35357/v2.0/ user create tester --password testing
    openstack --os-token ADMIN --os-url http://127.0.0.1:35357/v2.0/ role add --user tester --project test admin

Configure Swift to work with Keystone
-------------------------------------
Edit the file /etc/swift/proxy-server.conf as follows:

1. Use keystone instead of tmpauth

::

    sudo sed -i '0,/tempauth/{s/tempauth/authtoken keystoneauth/}' /etc/swift/proxy-server.conf

2. Add the following blocks at the end of /etc/swift/proxy-server.conf

::

    [filter:authtoken]
    paste.filter_factory = keystonemiddleware.auth_token:filter_factory
    auth_url=http://127.0.0.1:35357
    auth_type=password
    insecure=true
    project_name=service
    username=swift
    password=passw0rd
    delay_auth_decision = True

    [filter:keystoneauth]
    use = egg:swift#keystoneauth

Restart the proxy server

::

    sudo swift-init proxy-server restart


We now test that the setup by having the user 'tester' to stat the account 'test'. We use the Swift client cli.
A convenient way to do so is to edit the user's .bashrc adding the lines:

::

    export OS_USERNAME=tester
    export OS_PASSWORD=testing
    export OS_TENANT_NAME=test
    export OS_AUTH_URL=http://127.0.0.1:5000/v2.0

Now do:

::

    source .bashrc
    swift stat

Install Storlets
================

Install Dependencies
--------------------
We need the following for the Java parts

::

    sudo add-apt-repository -y ppa:openjdk-r/ppa
    sudo apt-get update
    sudo apt-get install -y openjdk-8-jdk
    sudo apt-get install -y ant

We need the following for Docker

::

    sudo apt-get -y install docker.io
    ln -sf /usr/bin/docker.io /usr/local/bin/docker
    sed -i '$acomplete -F _docker docker' /etc/bash_completion.d/docker
    update-rc.d docker defaults

Get and build the storlets code
-------------------------------

::

    cd $HOME
    git clone https://github.com/openstack/storlets.git
    cd storlets
    ant build
    cd -

Build the Docker image to be used for running storlets
------------------------------------------------------
Step 1: Create a working space for building the docker images, e.g.

::

    mkdir -p $HOME/docker_repos
    sudo docker pull ubuntu:14_04

Step 2: Create a Docker image with Java

::

    mkdir -p $HOME/docker_repos/ubuntu_14.04_jre8
    cd $HOME/docker_repos/ubuntu_14.04_jre8
    cp $HOME/storlets/Engine/dependencies/logback-classic-1.1.2.jar .
    cp $HOME/storlets/Engine/dependencies/logback-core-1.1.2.jar .
    cp $HOME/storlets/Engine/dependencies/slf4j-api-1.7.7.jar .
    cp $HOME/storlets/Engine/dependencies/json_simple-1.1.jar .
    cp $HOME/storlets/Engine/dependencies/logback.xml .
    cd -

Create the file: $HOME/docker_repos/ubuntu_14.04_jre8/Dockerfile
with the following content:

::

    FROM ubuntu:14.04
    MAINTAINER root

    # The following operations shoud be defined in one line
    # to prevent docker images from including apt cache file.
    RUN apt-get update && \
    apt-get install python -y && \
    apt-get install software-properties-common -y && \
    add-apt-repository ppa:openjdk-r/ppa -y && \
    apt-get update && \
    apt-get install openjdk-8-jre -y && \
    apt-get clean

    COPY logback-classic-1.1.2.jar  /opt/storlets/
    RUN ["chmod", "0744", "/opt/storlets/logback-classic-1.1.2.jar"]

    COPY logback-core-1.1.2.jar /opt/storlets/
    RUN ["chmod", "0744", "/opt/storlets/logback-core-1.1.2.jar"]

    COPY logback.xml    /opt/storlets/
    RUN ["chmod", "0744", "/opt/storlets/logback.xml"]

    COPY slf4j-api-1.7.7.jar    /opt/storlets/
    RUN ["chmod", "0744", "/opt/storlets/slf4j-api-1.7.7.jar"]

    COPY json_simple-1.1.jar    /opt/storlets/
    RUN ["chmod", "0744", "/opt/storlets/json_simple-1.1.jar"]

Build the image

::

    cd $HOME/docker_repos/ubuntu_14.04_jre8
    sudo docker build -q -t ubuntu_14.04_jre8 .
    cd -


Step 3: Augment the above created image with the storlets stuff

::

    mkdir -p $HOME/docker_repos/ubuntu_14.04_jre8_storlets
    cd $HOME/docker_repos/ubuntu_14.04_jre8_storlets
    cp $HOME/storlets/Engine/SBus/SBusJavaFacade/bin/libjsbus.so .
    cp $HOME/storlets/Engine/SBus/SBusJavaFacade/bin/SBusJavaFacade.jar .
    cp $HOME/storlets/Engine/SBus/SBusPythonFacade/dist/SBusPythonFacade-1.0.linux-x86_64.tar.gz .
    cp $HOME/storlets/Engine/SBus/SBusTransportLayer/bin/sbus.so .
    cp $HOME/storlets/Engine/SDaemon/bin/SDaemon.jar .
    cp $HOME/storlets/Engine/SCommon/bin/SCommon.jar .
    cp $HOME/storlets/Engine/agent/dist/storlets_agent-1.0.linux-x86_64.tar.gz .
    cp $HOME/storlets/install/storlets/roles/docker_storlet_engine_image/files/init_container.sh .
    cd -

Create the file: $HOME/docker_repos/ubuntu_14.04_jre8_storlets/Dockerfile
with the following content:

::

    FROM ubuntu_14.04_jre8

    MAINTAINER root

    RUN [ "groupadd", "-g", "1003", "swift" ]
    RUN [ "useradd", "-u" , "1003", "-g", "1003", "swift" ]

    ADD SBusPythonFacade-1.0.linux-x86_64.tar.gz            /
    RUN chmod -R 0755 /usr/local/lib/python2.7/dist-packages/SBusPythonFacade*

    COPY sbus.so                                            /usr/local/lib/python2.7/dist-packages/
    RUN ["chmod", "0755", "/usr/local/lib/python2.7/dist-packages/sbus.so"]

    COPY SBusJavaFacade.jar                                 /opt/storlets/
    RUN ["chmod", "0744", "/opt/storlets/SBusJavaFacade.jar"]

    COPY libjsbus.so                                        /opt/storlets/
    RUN ["chmod", "0755", "/opt/storlets/libjsbus.so"]

    COPY SDaemon.jar                                        /opt/storlets/
    RUN ["chmod", "0744", "/opt/storlets/SDaemon.jar"]

    COPY SCommon.jar                                        /opt/storlets/
    RUN ["chmod", "0744", "/opt/storlets/SCommon.jar"]

    ADD storlets_agent-1.0.linux-x86_64.tar.gz      /
    RUN ["chmod", "0755", "/usr/local/bin/storlets-daemon-factory"]

    COPY init_container.sh                                  /opt/storlets/
    RUN ["chmod", "0755", "/opt/storlets/init_container.sh"]

    CMD ["prod", "/mnt/channels/factory_pipe","DEBUG"]
    ENTRYPOINT ["/opt/storlets/init_container.sh"]

Build the image

::

    cd $HOME/docker_repos/ubuntu_14.04_jre8_storlets
    sudo docker build -q -t ubuntu_14.04_jre8_storlets .
    cd -

Step 4: Create a tenant specific image. The engine looks for images
having the name <tenand id>.
First, we get the tenant id. Using the Swift cli and the above create user do:

::

    swift --os-auth-url http://127.0.0.1:5000/v2.0 --os-tenant-name service --os-username swift --os-password passw0rd stat

The response from the above contains the account line, e.g.:

::

    Account: AUTH_719caee804974c14a8632a760a7f85f7

The account id is the number following the 'AUTH\_' prefix.

Next create the file $HOME/docker_repos/ubuntu_14.04_jre8_storlets_<account id>/Dockerfile
with the following content:

::

    FROM ubuntu_14.04_jre8_storlets

    MAINTAINER root

    RUN apt-get install vim

Build the image

::

    cd $HOME/docker_repos/ubuntu_14.04_jre8_storlets_<account id>
    sudo docker build -q -t <account id> .
    cd -

Install the storlets middleware components
------------------------------------------
Install the SBus components used for comuunication between the host and container

::

    cp $HOME/storlets/SBusPythonFacade/dist/SBusPythonFacade-1.0.linux-x86_64.tar.gz /tmp
    cd /tmp
    sudo tar -C / -xvf SBusPythonFacade-1.0.linux-x86_64.tar.gz
    sudo cp $HOME/storlets/Engine/SBus/SBusTransportLayer/bin/sbus.so /usr/local/lib/python2.7/dist-packages/sbus.so
    sudo chown $USER:$USER /usr/local/lib/python2.7/dist-packages/sbus.so

Install the swift middleware

::

    cp $HOME/storlets/Engine/swift/dist/storlets-1.0.linux-x86_64.tar.gz /tmp
    cd /tmp
    sudo tar -C / -xvf storlets-1.0.linux-x86_64.tar.gz

Create the storlets run time environment
----------------------------------------
Create the run time directory

::

    export STORLETS_HOME=/home/docker_device
    sudo mkdir -p $STORLETS_HOME
    sudo chmod 777 $STORLETS_HOME

Create the scripts directory and populate it.
Note that these scripts are executed by the middleware but
require root privileges.

::

    mkdir $STORLETS_HOME/scripts
    cd STORLETS_HOME/scripts
    cp $HOME/storlets/Engine/SMScripts/bin/restart_docker_container .
    sudo chown root:root restart_docker_container
    sudo chmod 04755 restart_docker_container
    cp $HOME/storlets/Engine/SMScripts/send_halt_cmd_to_daemon_factory.py .
    sudo chown root:root send_halt_cmd_to_daemon_factory.py
    sudo chmod 04755 send_halt_cmd_to_daemon_factory.py

The run time directory will be later populated by the middleware with:
 #. storlets - Docker container mapped directories keeping storlet jars
 #. pipe - A Docker container mapped directories holding named pipes shared between the middleware and the containers.
 #. logs - the logs of storlets running inside the docker containers
 #. cache - a local cache for storlet jars

Configure Swift to work with the middleware components
------------------------------------------------------
Step 1: Edit the proxy server config file /etc/swift/proxy-server.conf and
do the following:

 #. Add the storlet_handler to the proxy server pipline just before the slo middleware as shown below:

 ::

    pipeline = catch_errors gatekeeper healthcheck proxy-logging cache container_sync bulk tempurl ratelimit authtoken keystoneauth container-quotas account-quotas storlet_handler slo dlo versioned_writes proxy-logging proxy-server

 #. At the bottom of the file add the following configuration block:

 ::

    [filter:storlet_handler]
    use = egg:storlets#storlet_handler
    storlet_container = storlet
    storlet_dependency = dependency
    storlet_timeout = 40
    storlet_gateway_module = docker
    storlet_gateway_conf = /etc/swift/storlet_docker_gateway.conf
    storlet_execute_on_proxy_only = false
    execution_server = proxy

Step 2: Edit the object server(s) config file(s).
In a SAIO environment these would be:
/etc/swift/object-server/1.conf through /etc/swift/object-server/4.conf
otherwise the file is typically /etc/swift/object-server.conf

 1. Add the storlet_handler to the object server pipline just before the slo object-server as shown below:

 ::

    pipeline = recon storlet_handler object-server

 2. At the bottom of the file add the following configuration block:

 ::

    [filter:storlet_handler]
    use = egg:storlets#storlet_handler
    storlet_container = storlet
    storlet_dependency = dependency
    storlet_timeout = 40
    storlet_gateway_module = docker
    storlet_gateway_conf = /etc/swift/storlet_docker_gateway.conf
    storlet_execute_on_proxy_only = false
    execution_server = object

Step 3: Add the Docker gateway configuration file.
Under /etc/swift create a file named storlet_docker_gateway.conf
with the following content:

::

    [DEFAULT]
    storlet_logcontainer = storletlog
    lxc_root = /home/docker_device/scopes
    cache_dir = /home/docker_device/cache/scopes
    log_dir = /home/docker_device/logs/scopes
    script_dir = /home/docker_device/scripts
    storlets_dir = /home/docker_device/storlets/scopes
    pipes_dir = /home/docker_device/pipes/scopes
    docker_repo =
    restart_linux_container_timeout = 3

Step 4:
Create and edit the file /etc/swift/storlet-proxy-server.conf:

::

    cp /etc/swift/proxy-server.conf /etc/swift/storlet-proxy-server.conf

Change the pipeline in /etc/swift/storlet-proxy-server.conf to be:

::

    pipeline = proxy-logging cache slo proxy-logging proxy-server

Step 5: restart swift

::

    sudo swift-init all restart

Enable the account for storlets
-------------------------------
We use the same test account and tester user created above.
To enable the account for storlets we need to set an appropriate
user metadata on the account and create within the account the
various Swift containers assumed by the engine.

We use the swift cli as follows:

::

  swift post \
  --os-auth-url=http://127.0.0.1:5000/v2.0 \
  --os-username=tester \
  --os-password=testing \
  --os-tenant-name=test \
  --meta "Storlet-Enabled:True"


  swift post \
  --os-auth-url=http://127.0.0.1:5000/v2.0 \
  --os-username=tester \
  --os-password=testing \
  --os-tenant-name=test \
  storlet

  swift post \
  --os-auth-url=http://127.0.0.1:5000/v2.0 \
  --os-username=tester \
  --os-password=testing \
  --os-tenant-name=test \
  dependency

  swift post \
  --os-auth-url=http://127.0.0.1:5000/v2.0 \
  --os-username=tester \
  --os-password=testing \
  --os-tenant-name=test \
  storletlog

Run the functional tests
------------------------
The functional tests upload various storlets and execute them.
Running the functional tests successfully proves the installation
completed successfully.

The functional tests are designed to run over a clustered installation
(that is not an all in one install). Hence, running the tests require
a cluster connfiguration file.

Step 1: Create the file $HOME/storlets/cluster_config.json with the below
content.

::

    {
        "groups" : {
            "storlet-mgmt": [ "127.0.0.1" ],
            "storlet-proxy": [ "127.0.0.1" ],
            "storlet-storage": [ "127.0.0.1" ],
            "docker": [ "127.0.0.1" ]
        },
        "all" : {
            "docker_device": "/home/docker_device",
            "storlet_source_dir": "~/storlets",
            "python_dist_packages_dir": "usr/local/lib/python2.7/dist-packages",
            "storlet_gateway_conf_file": "/etc/swift/storlet_docker_gateway.conf",
            "keystone_endpoint_host": "127.0.0.1",
            "keystone_admin_url": "http://127.0.0.1:35357/v2.0",
            "keystone_public_url": "http://127.0.0.1:5000/v2.0",
            "swift_endpoint_host": "127.0.0.1",
            "swift_public_url": "http://127.0.0.1:8080/v1",
            "storlets_enabled_attribute_name": "storlet-enabled",
            "storlets_default_tenant_name": "test",
            "storlets_default_tenant_user_name": "tester",
            "storlets_default_tenant_user_password": "testing"
        }
    }

Step 2: Run the functional tests

::

    cd $HOME/storlets
    ./.functests dev
