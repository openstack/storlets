Installing a Development Environment
====================================
This guide gives a step by step installation instructions that are equivalent
to what s2aio.sh does. The intention is to make the reader more familiar with
what is involved in installing Storlets on top of Swift

The below steps must be executed using a passwordless sudoer user.

Install Swift and Keystone using devstack
-----------------------------------------

Clone devstack:

::

    git clone https://opendev.org/openstack/devstack.git

Create a localrc file under the devstack repository root directory:

::

    ENABLE_HTTPD_MOD_WSGI_SERVICES=False
    ENABLED_SERVICES=key,swift,mysql
    HOST_IP=127.0.0.1
    ADMIN_PASSWORD=admin
    MYSQL_PASSWORD=$ADMIN_PASSWORD
    RABBIT_PASSWORD=$ADMIN_PASSWORD
    SERVICE_PASSWORD=$ADMIN_PASSWORD

    OS_IDENTITY_API_VERSION=3
    OS_AUTH_URL="http://$KEYSTONE_IP/identity/v3"
    OS_USERNAME=$ADMIN_USER
    OS_USER_DOMAIN_ID=default
    OS_PASSWORD=$ADMIN_PASSWORD
    OS_PROJECT_NAME=$ADMIN_USER
    OS_PROJECT_DOMAIN_ID=default
    OS_REGION_NAME=RegionOne

    SERVICE_HOST=$SWIFT_IP
    SWIFT_SERVICE_PROTOCOL=${SWIFT_SERVICE_PROTOCOL:-http}
    SWIFT_DEFAULT_BIND_PORT=${SWIFT_DEFAULT_BIND_PORT:-8080}
    # service local host is used for ring building
    SWIFT_SERVICE_LOCAL_HOST=$HOST_IP
    # service listen address for prox
    SWIFT_SERVICE_LISTEN_ADDRESS=$HOST_IP
    SWIFT_LOOPBACK_DISK_SIZE=20G
    SWIFT_MAX_FILE_SIZE=5368709122
    SWIFT_HASH=1234567890
    IDENTITY_API_VERSION=3

Run the stack.sh script.
Before proceeding, we need to stop the
swift instances that were executed by the
stack.sh script. From the same directory do:

::

    source functions
    source lib/swift
    stop_swift

Finally, add the swift devices to fstab:

::

    sudo sh -c 'echo "/opt/stack/data/swift/drives/images/swift.img /opt/stack/data/swift/drives/sdb1 xfs loop" >> /etc/fstab'

Configure a user and project in Keystone
----------------------------------------

We use the openstack cli to configure a user and project
used by the storlets functional tests. We start by
defining some environment variables:

::

    export OS_IDENTITY_API_VERSION=3
    export OS_AUTH_URL="http://$KEYSTONE_IP/identity/v3"
    export OS_USERNAME=$ADMIN_USER
    export OS_USER_DOMAIN_ID=default
    export OS_PASSWORD=$ADMIN_PASSWORD
    export OS_PROJECT_NAME=$ADMIN_USER
    export OS_PROJECT_DOMAIN_ID=default
    export OS_REGION_NAME=RegionOne

We now create the project and users with Keystone.

::

    openstack project create test
    openstack user create --project test --password testing tester
    openstack role add --user tester --project test admin
    openstack user create --project test --password member tester_member
    openstack role add --user tester --project test _member_

We now test that the setup by having the user 'tester' to stat the account 'test'. We use the Swift client cli.
A convenient way to do so is to edit the user's .bashrc adding the lines:

::

    export OS_USERNAME=tester
    export OS_PASSWORD=testing
    export OS_TENANT_NAME=test
    export OS_AUTH_URL=http://127.0.0.1/identity/v3

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

    sudo apt-get install openjdk-11-jdk ant

We need the following for Docker

::

    sudo apt-get install docker.io
    ln -sf /usr/bin/docker.io /usr/local/bin/docker
    sed -i '$acomplete -F _docker docker' /etc/bash_completion.d/docker
    update-rc.d docker defaults

Also, add swift user to docker group so that the user can manage docker
containers without sudo

::

    sudo usermod -aG docker swift


Get and install the storlets code
---------------------------------

::

    cd $HOME
    git clone https://opendev.org/openstack/storlets.git
    cd storlets
    sudo ./install_libs.sh
    sudo python setup.py install
    cd -

.. note:: You don't need sudo for 'python setup.py install' when installing the storlets package into your python virtualenv.

Build the Docker image to be used for running storlets
------------------------------------------------------
Step 1: Create a working space for building the docker images, e.g.

::

    mkdir -p $HOME/docker_repos
    sudo docker pull ubuntu:22.04

Step 2: Create a Docker image with Java

::

    mkdir -p $HOME/docker_repos/ubuntu_22.04_jre11

Create the file: $HOME/docker_repos/ubuntu_22.04_jre11/Dockerfile
with the following content:

::

    FROM ubuntu:22.04
    MAINTAINER root

    # The following operations should be defined in one line
    # to prevent docker images from including apt cache file.
    RUN apt-get update && \
    apt-get install python3 && \
    apt-get install software-properties-common && \
    apt-get install openjdk-11-jre-headless ant  && \
    apt-get clean

Build the image and name it *storlet_engine_image*.

::

    cd $HOME/docker_repos/ubuntu_22.04_jre11
    sudo docker build -t storlet_engine_image .
    cd -

Step 3: Create a tenant specific image. The engine looks for images
having the name <tenand id>.
First, we get the tenant id. Using the Swift cli and the above create user do:

::

    swift --os-auth-url http://127.0.0.1/identity/v3 --os-project-name test --os-project-domain-name default --os-username tester --os-password testing stat

The response from the above contains the account line, e.g.:

::

    Account: AUTH_719caee804974c14a8632a760a7f85f7

The account id is the number following the 'AUTH\_' prefix.

Next create the file $HOME/docker_repos/storlet_engine_image_<account id>/Dockerfile
with the following content:

::

    FROM storlet_engine_image
    MAINTAINER root


Build the image

::

    cd $HOME/docker_repos/storlet_engine_image_<account id>
    sudo docker build -t <account id> .
    cd -

Create the storlets run time environment
----------------------------------------
Create the run time directory

::

    export STORLETS_HOME=/var/lib/storlets
    sudo mkdir -p $STORLETS_HOME
    sudo chmod 777 $STORLETS_HOME

The run time directory will be later populated by the middleware with:
 #. storlets - Docker container mapped directories keeping storlet jars
 #. pipe - A Docker container mapped directories holding named pipes shared between the middleware and the containers.
 #. logs - the logs of storlets running inside the docker containers
 #. cache - a local cache for storlet jars

Configure Swift to work with the middleware components
------------------------------------------------------
Step 1: Edit the proxy server config file /etc/swift/proxy-server.conf and
do the following:

 #. Add the storlet_handler to the proxy server pipeline just before the slo middleware as shown below:

 ::

    pipeline = catch_errors gatekeeper healthcheck proxy-logging cache container_sync bulk tempurl ratelimit authtoken keystoneauth container-quotas account-quotas storlet_handler slo dlo versioned_writes proxy-logging proxy-server

 #. At the bottom of the file add the following configuration block:

 ::

    [filter:storlet_handler]
    use = egg:storlets#storlet_handler
    storlet_container = storlet
    storlet_dependency = dependency
    storlet_gateway_module = docker
    storlet_gateway_conf = /etc/swift/storlet_docker_gateway.conf
    storlet_execute_on_proxy_only = false
    execution_server = proxy

Step 2: Edit the object server(s) config file(s).
In a SAIO environment these would be:
/etc/swift/object-server/1.conf through /etc/swift/object-server/4.conf
otherwise the file is typically /etc/swift/object-server.conf

 1. Add the storlet_handler to the object server pipeline just before the slo object-server as shown below:

 ::

    pipeline = recon storlet_handler object-server

 2. At the bottom of the file add the following configuration block:

 ::

    [filter:storlet_handler]
    use = egg:storlets#storlet_handler
    storlet_container = storlet
    storlet_dependency = dependency
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
    host_root = /var/lib/storlets
    cache_dir = /var/lib/storlets/cache/scopes
    log_dir = /var/lib/storlets/logs/scopes
    script_dir = /var/lib/storlets/scripts
    storlets_dir = /var/lib/storlets/storlets/scopes
    pipes_dir = /var/lib/storlets/pipes/scopes
    storlet_timeout = 40
    container_image_namespace =
    restart_linux_container_timeout = 3

Step 4: restart swift

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
  --os-auth-url=http://127.0.0.1/identity/v3 \
  --os-username=tester \
  --os-password=testing \
  --os-project-name=test \
  --os-project-domain-name default \
  --meta "Storlet-Enabled:True"


  swift post \
  --os-auth-url=http://127.0.0.1/identity/v3 \
  --os-username=tester \
  --os-password=testing \
  --os-project-name=test \
  --os-project-domain-name default \
  --read-acl test:tester_member \
  storlet

  swift post \
  --os-auth-url=http://127.0.0.1/identity/v3 \
  --os-username=tester \
  --os-password=testing \
  --os-project-name=test \
  --os-project-domain-name default \
  --read-acl test:tester_member \
  dependency

  swift post \
  --os-auth-url=http://127.0.0.1/identity/v3 \
  --os-username=tester \
  --os-password=testing \
  --os-project-name=test \
  --os-project-domain-name default \
  storletlog

Run the functional tests
------------------------
The functional tests upload various storlets and execute them.
Running the functional tests successfully proves the installation
completed successfully.

The functional tests are designed to run over a clustered installation
(that is not an all in one install). Hence, running the tests require
a cluster connfiguration file.

Step 1: Create the file $HOME/storlets/test.conf with the below
content.

::

    [general]
    region = RegionOne
    storlets_default_project_member_password = member
    storlets_default_project_member_user = tester_member
    storlets_default_project_user_password = testing
    storlets_default_project_user_name = tester
    storlets_default_project_name = test
    keystone_public_url = http://127.0.0.1/identity/v3
    keystone_default_domain = default

Step 2: Run the functional tests

::

    cd $HOME/storlets
    ant build_storlets
    tox -e func
