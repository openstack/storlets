#!/bin/bash
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

# Functions to control the configuration and operation of the **Swift** service

# Dependencies:
#
# - ``functions`` file
# - ``functions-common`` file
# - ``STACK_USER`` must be defined
# - ``SWIFT_DATA_DIR`` or ``DATA_DIR`` must be defined
# - ``lib/swift`` file
# - ``lib/keystone`` file
#
# - install_storlets
# TODO(eranr):
# Add clean_storlets

# Save trace setting
_XTRACE_LIB_SWIFT=$(set +o | grep xtrace)
set +o xtrace

# Defaults
# --------

# General devstack install tunables
ADMIN_USER=admin
ADMIN_PASSWORD=admin
ADMIN_PROJECT=admin

SWIFT_DEFAULT_PROJECT=test
SWIFT_DEFAULT_USER=tester
SWIFT_DEFAULT_USER_PWD=testing
SWIFT_MEMBER_USER=tester_member
SWIFT_MEMBER_USER_PWD=member

# Storlets install tunables
STORLETS_DEFAULT_USER_DOMAIN_ID=${STORLETS_DEFAULT_USER_DOMAIN_ID:-default}
STORLETS_DEFAULT_PROJECT_DOMAIN_ID=${STORLETS_DEFAULT_PROJECT_DOMAIN_ID:-default}
STORLET_MANAGEMENT_USER=${STORLET_MANAGEMENT_USER:-$USER}
STORLETS_DOCKER_DEVICE=${STORLETS_DOCKER_DEVICE:-/home/docker_device}
STORLETS_DOCKER_BASE_IMG=${STORLETS_DOCKER_BASE_IMG:-ubuntu:18.04}
STORLETS_DOCKER_BASE_IMG_NAME=${STORLETS_DOCKER_BASE_IMG_NAME:-ubuntu_18.04}
STORLETS_DOCKER_SWIFT_GROUP_ID=${STORLETS_DOCKER_SWIFT_GROUP_ID:-1003}
STORLETS_DOCKER_SWIFT_USER_ID=${STORLETS_DOCKER_SWIFT_USER_ID:-1003}
STORLETS_SWIFT_RUNTIME_USER=${STORLETS_SWIFT_RUNTIME_USER:-$USER}
STORLETS_SWIFT_RUNTIME_GROUP=${STORLETS_SWIFT_RUNTIME_GROUP:-$USER}
STORLETS_MIDDLEWARE_NAME=storlet_handler
STORLETS_STORLET_CONTAINER_NAME=${STORLETS_STORLET_CONTAINER_NAME:-storlet}
STORLETS_DEPENDENCY_CONTAINER_NAME=${STORLETS_DEPENDENCY_CONTAINER_NAME:-dependency}
STORLETS_LOG_CONTAIER_NAME=${STORLETS_LOG_CONTAIER_NAME:-log}
STORLETS_GATEWAY_MODULE=${STORLETS_GATEWAY_MODULE:-docker}
STORLETS_GATEWAY_CONF_FILE=${STORLETS_GATEWAY_CONF_FILE:-/etc/swift/storlet_docker_gateway.conf}
STORLETS_PROXY_EXECUTION_ONLY=${STORLETS_PROXY_EXECUTION_ONLY:-false}
STORLETS_SCRIPTS_DIR=${STORLETS_SCRIPTS_DIR:-"$STORLETS_DOCKER_DEVICE"/scripts}
STORLETS_STORLETS_DIR=${STORLETS_STORLETS_DIR:-"$STORLETS_DOCKER_DEVICE"/storlets/scopes}
STORLETS_LOGS_DIR=${STORLETS_LOGS_DIR:-"$STORLETS_DOCKER_DEVICE"/logs/scopes}
STORLETS_CACHE_DIR=${STORLETS_CACHE_DIR:-"$STORLETS_DOCKER_DEVICE"/cache/scopes}
STORLETS_PIPES_DIR=${STORLETS_PIPES_DIR:-"$STORLETS_DOCKER_DEVICE"/pipes/scopes}
STORLETS_RESTART_CONTAINER_TIMEOUT=${STORLETS_RESTART_CONTAINER_TIMEOUT:-3}
STORLETS_RUNTIME_TIMEOUT=${STORLETS_RUNTIME_TIMEOUT:-40}

TMP_REGISTRY_PREFIX=/tmp/registry

# Functions
# ---------

_storlets_swift_start() {
    swift-init --run-dir=${SWIFT_DATA_DIR}/run all start || true
}

_storlets_swift_stop() {
    swift-init --run-dir=${SWIFT_DATA_DIR}/run all stop || true
}

_storlets_swift_restart() {
    swift-init --run-dir=${SWIFT_DATA_DIR}/run all restart || true
}

_export_os_vars() {
    export OS_IDENTITY_API_VERSION=3
    export OS_AUTH_URL="http://$KEYSTONE_IP/identity/v3"
    export OS_REGION_NAME=RegionOne
}

_export_keystone_os_vars() {
    _export_os_vars
    export OS_USERNAME=$ADMIN_USER
    export OS_USER_DOMAIN_ID=$STORLETS_DEFAULT_USER_DOMAIN_ID
    export OS_PASSWORD=$ADMIN_PASSWORD
    export OS_PROJECT_NAME=$ADMIN_USER
    export OS_PROJECT_DOMAIN_ID=$STORLETS_DEFAULT_PROJECT_DOMAIN_ID
}

_export_swift_os_vars() {
    _export_os_vars
    export OS_USERNAME=$SWIFT_DEFAULT_USER
    export OS_USER_DOMAIN_ID=$STORLETS_DEFAULT_USER_DOMAIN_ID
    export OS_PASSWORD=$SWIFT_DEFAULT_USER_PWD
    export OS_PROJECT_NAME=$SWIFT_DEFAULT_PROJECT
    export OS_PROJECT_DOMAIN_ID=$STORLETS_DEFAULT_PROJECT_DOMAIN_ID
}

configure_swift_and_keystone_for_storlets() {
    # Add project and users to Keystone
    _export_keystone_os_vars
    project_test_created=$(openstack project list | grep -w $SWIFT_DEFAULT_PROJECT | wc -l)
    if [ $project_test_created -eq 0 ]; then
        openstack project create $SWIFT_DEFAULT_PROJECT
    fi
    user_tester_created=$(openstack user list | grep -w $SWIFT_DEFAULT_USER | wc -l)
    if [ $user_tester_created -eq 0 ]; then
        openstack user create --project $SWIFT_DEFAULT_PROJECT --password $SWIFT_DEFAULT_USER_PWD $SWIFT_DEFAULT_USER
        openstack role add --user $SWIFT_DEFAULT_USER --project $SWIFT_DEFAULT_PROJECT admin
    fi
    member_user_tester_created=$(openstack user list | grep -w $SWIFT_MEMBER_USER | wc -l)
    if [ $member_user_tester_created -eq 0 ]; then
        role_member_created=$(openstack role list | grep -w _member_ | wc -l)
        if [ $role_member_created -eq 0 ]; then
            openstack role create _member_
        fi
        openstack user create --project $SWIFT_DEFAULT_PROJECT --password $SWIFT_MEMBER_USER_PWD $SWIFT_MEMBER_USER
        openstack role add --user $SWIFT_MEMBER_USER --project $SWIFT_DEFAULT_PROJECT _member_
    fi

    # Modify relevant Swift configuration files
    _generate_swift_middleware_conf
    _generate_storlet-docker-gateway
    sudo python devstack/swift_config.py install /tmp/swift_middleware_conf $STORLETS_SWIFT_RUNTIME_USER
    rm /tmp/swift_middleware_conf
    rm /tmp/storlet-docker-gateway.conf

    # Create storlet related containers and set ACLs
    _storlets_swift_start
    _export_swift_os_vars
    openstack object store account set --property Storlet-Enabled=True
    swift post --read-acl $SWIFT_DEFAULT_PROJECT:$SWIFT_MEMBER_USER $STORLETS_STORLET_CONTAINER_NAME
    swift post --read-acl $SWIFT_DEFAULT_PROJECT:$SWIFT_MEMBER_USER $STORLETS_DEPENDENCY_CONTAINER_NAME
    swift post $STORLETS_LOG_CONTAIER_NAME
}

_install_docker() {
    # TODO: Add other dirstors.
    # This one is geared towards Ubuntu
    # See other projects that install docker
    DOCKER_UNIX_SOCKET=/var/run/docker.sock
    DOCKER_SERVICE_TIMEOUT=5

    install_package socat
    wget http://get.docker.com -O install_docker.sh
    sudo chmod 777 install_docker.sh
    sudo bash -x install_docker.sh
    sudo rm install_docker.sh

    sudo killall docker || true

    # systemd env doesn't require /etc/default/docker options
    if [[ ! -e /etc/default/docker ]]; then
        sudo touch /etc/default/docker
        sudo ls /lib/systemd/system
        sudo sed -i '0,/[service]/a EnvironmentFile=-/etc/default/docker' /lib/systemd/system/docker.service
        sudo cat /lib/systemd/system/docker.service
    fi
    sudo cat /etc/default/docker
    sudo sed -r 's#^.*DOCKER_OPTS=.*$#DOCKER_OPTS="--debug -g /home/docker_device/docker --storage-opt dm.override_udev_sync_check=true"#' /etc/default/docker

    # Start the daemon - restart just in case the package ever auto-starts...
    restart_service docker

    echo "Waiting for docker daemon to start..."
    DOCKER_GROUP=$(groups | cut -d' ' -f1)
    CONFIGURE_CMD="while ! /bin/echo -e 'GET /version HTTP/1.0\n\n' | socat - unix-connect:$DOCKER_UNIX_SOCKET 2>/dev/null | grep -q '200 OK'; do
      # Set the right group on docker unix socket before retrying
      sudo chgrp $DOCKER_GROUP $DOCKER_UNIX_SOCKET
      sudo chmod g+rw $DOCKER_UNIX_SOCKET
      sleep 1
    done"
    if ! timeout $DOCKER_SERVICE_TIMEOUT sh -c "$CONFIGURE_CMD"; then
      die $LINENO "docker did not start"
fi
}

prepare_storlets_install() {
    sudo mkdir -p "$STORLETS_DOCKER_DEVICE"/docker
    sudo chmod 777 $STORLETS_DOCKER_DEVICE
    _install_docker
    sudo add-apt-repository -y ppa:openjdk-r/ppa
    sudo apt-get update
    sudo apt-get install -y openjdk-8-jdk-headless
    sudo apt-get install -y ant
    sudo apt-get install -y python
    sudo apt-get install -y python-setuptools
    sudo apt-get install -y python3.5
    sudo apt-get install -y python3-setuptools
}

_generate_jre_dockerfile() {
    cat <<EOF > ${TMP_REGISTRY_PREFIX}/repositories/${STORLETS_DOCKER_BASE_IMG_NAME}_jre8/Dockerfile
FROM $STORLETS_DOCKER_BASE_IMG
MAINTAINER root

RUN apt-get update && \
    apt-get install python -y && \
    apt-get install python3.5 -y && \
    apt-get install git -y && \
    apt-get update && \
    apt-get install openjdk-8-jre-headless -y && \
    apt-get clean
EOF
}

create_base_jre_image() {
    echo "Create base jre image"
    docker pull $STORLETS_DOCKER_BASE_IMG
    mkdir -p ${TMP_REGISTRY_PREFIX}/repositories/"$STORLETS_DOCKER_BASE_IMG_NAME"_jre8
    _generate_jre_dockerfile
    cd ${TMP_REGISTRY_PREFIX}/repositories/"$STORLETS_DOCKER_BASE_IMG_NAME"_jre8
    docker build -q -t ${STORLETS_DOCKER_BASE_IMG_NAME}_jre8 .
    cd -
}

_generate_logback_xml() {
    cat <<EOF > ${TMP_REGISTRY_PREFIX}/repositories/"$STORLETS_DOCKER_BASE_IMG_NAME"_jre8_storlets/logback.xml
<configuration>
  <appender name="FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
    <file>/tmp/SDaemon.log</file>
    <rollingPolicy class="ch.qos.logback.core.rolling.TimeBasedRollingPolicy">
            <!-- daily rollover. Make sure the path matches the one in the file element or else
             the rollover logs are placed in the working directory. -->
            <fileNamePattern>/srv/logs/application_%d{yyyy-MM-dd}.%i.log</fileNamePattern>

            <timeBasedFileNamingAndTriggeringPolicy class="ch.qos.logback.core.rolling.SizeAndTimeBasedFNATP">
                <maxFileSize>1MB</maxFileSize>
            </timeBasedFileNamingAndTriggeringPolicy>
            <!-- keep 30 days' worth of history -->
            <maxHistory>30</maxHistory>
    </rollingPolicy>
    <encoder>
        <pattern>%-4relative [%thread] %-5level %logger{35} - %msg%n</pattern>
    </encoder>
  </appender>

  <root level="TRACE">
    <appender-ref ref="FILE" />
  </root>
</configuration>
EOF
}

_generate_jre_storlet_dockerfile() {
    cat <<EOF > ${TMP_REGISTRY_PREFIX}/repositories/"$STORLETS_DOCKER_BASE_IMG_NAME"_jre8_storlets/Dockerfile
FROM ${STORLETS_DOCKER_BASE_IMG_NAME}_jre8
MAINTAINER root
RUN [ "groupadd", "-g", "$STORLETS_DOCKER_SWIFT_GROUP_ID", "swift" ]
RUN [ "useradd", "-u" , "$STORLETS_DOCKER_SWIFT_USER_ID", "-g", "$STORLETS_DOCKER_SWIFT_GROUP_ID", "swift" ]

# Copy files
COPY ["logback.xml", "/usr/local/lib/storlets/"]

RUN ["chmod", "0744", "/usr/local/lib/storlets/logback.xml"]

CMD ["prod", "/mnt/channels/factory_pipe", "DEBUG"]

ENTRYPOINT ["/usr/local/libexec/storlets/init_container.sh"]
EOF
}

create_storlet_engine_image() {
    echo "Create Storlet engine image"
    mkdir -p ${TMP_REGISTRY_PREFIX}/repositories/"$STORLETS_DOCKER_BASE_IMG_NAME"_jre8_storlets
    _generate_logback_xml
    _generate_jre_storlet_dockerfile
    cd ${TMP_REGISTRY_PREFIX}/repositories/"$STORLETS_DOCKER_BASE_IMG_NAME"_jre8_storlets
    docker build -q -t ${STORLETS_DOCKER_BASE_IMG_NAME}_jre8_storlets .
    cd -
}

install_storlets_code() {
    echo "Installing storlets"
    cd $REPO_DIR
    sudo ./install_libs.sh
    sudo pip install -r requirements.txt
    sudo python setup.py install
    sudo pip3 install -r requirements.txt
    sudo python3 setup.py install
    sudo chown -R ${STORLETS_SWIFT_RUNTIME_USER} storlets.egg-info*

    sudo mkdir -p $STORLETS_DOCKER_DEVICE/scripts
    sudo chown "$STORLETS_SWIFT_RUNTIME_USER":"$STORLETS_SWIFT_RUNTIME_GROUP" "$STORLETS_DOCKER_DEVICE"/scripts
    sudo chmod 0755 "$STORLETS_DOCKER_DEVICE"/scripts
    sudo cp scripts/restart_docker_container "$STORLETS_DOCKER_DEVICE"/scripts/
    sudo chmod 04755 "$STORLETS_DOCKER_DEVICE"/scripts/restart_docker_container
    sudo chown root:root "$STORLETS_DOCKER_DEVICE"/scripts/restart_docker_container

    cd -
}

_generate_swift_middleware_conf() {
    cat <<EOF > /tmp/swift_middleware_conf
[proxy-confs]
proxy_server_conf_file = /etc/swift/proxy-server.conf
storlet_proxy_server_conf_file = /etc/swift/storlet-proxy-server.conf

[object-confs]
object_server_conf_files = /etc/swift/object-server/1.conf
#object_server_conf_files = /etc/swift/object-server/1.conf, /etc/swift/object-server/2.conf, /etc/swift/object-server/3.conf, /etc/swift/object-server/4.conf
#object_server_conf_files = /etc/swift/object-server.conf

[common-confs]
storlet_middleware = $STORLETS_MIDDLEWARE_NAME
storlet_container = $STORLETS_STORLET_CONTAINER_NAME
storlet_dependency = $STORLETS_DEPENDENCY_CONTAINER_NAME
#storlet_log = $STORLETS_LOG_CONTAIER_NAME
storlet_gateway_module = $STORLETS_GATEWAY_MODULE
storlet_gateway_conf = $STORLETS_GATEWAY_CONF_FILE
storlet_proxy_execution = $STORLETS_PROXY_EXECUTION_ONLY
EOF
}

_generate_storlet-docker-gateway() {
    cat <<EOF > /tmp/storlet-docker-gateway.conf
[DEFAULT]
storlet_logcontainer = $STORLETS_LOG_CONTAIER_NAME
cache_dir = $STORLETS_CACHE_DIR
log_dir = $STORLETS_LOGS_DIR
script_dir = $STORLETS_SCRIPTS_DIR
storlets_dir = $STORLETS_STORLETS_DIR
pipes_dir = $STORLETS_PIPES_DIR
restart_linux_container_timeout = $STORLETS_RESTART_CONTAINER_TIMEOUT
storlet_timeout = $STORLETS_RUNTIME_TIMEOUT
EOF
}

_generate_default_tenant_dockerfile() {
    cat <<EOF > ${TMP_REGISTRY_PREFIX}/repositories/"$SWIFT_DEFAULT_PROJECT_ID"/Dockerfile
FROM ${STORLETS_DOCKER_BASE_IMG_NAME}_jre8_storlets
MAINTAINER root
EOF
}

create_default_tenant_image() {
    SWIFT_DEFAULT_PROJECT_ID=`openstack project list | grep -w $SWIFT_DEFAULT_PROJECT | awk '{ print $2 }'`
    mkdir -p ${TMP_REGISTRY_PREFIX}/repositories/$SWIFT_DEFAULT_PROJECT_ID
    _generate_default_tenant_dockerfile
    cd ${TMP_REGISTRY_PREFIX}/repositories/$SWIFT_DEFAULT_PROJECT_ID
    docker build -q -t ${SWIFT_DEFAULT_PROJECT_ID:0:13} .
    cd -
}

create_test_config_file() {
    testfile=${REPO_DIR}/test.conf
    iniset ${testfile} general keystone_default_domain $STORLETS_DEFAULT_PROJECT_DOMAIN_ID
    iniset ${testfile} general keystone_public_url $KEYSTONE_PUBLIC_URL
    iniset ${testfile} general storlets_default_project_name $SWIFT_DEFAULT_PROJECT
    iniset ${testfile} general storlets_default_project_user_name $SWIFT_DEFAULT_USER
    iniset ${testfile} general storlets_default_project_user_password $SWIFT_DEFAULT_USER_PWD
    iniset ${testfile} general storlets_default_project_member_user $SWIFT_MEMBER_USER
    iniset ${testfile} general storlets_default_project_member_password $SWIFT_MEMBER_USER_PWD
    iniset ${testfile} general region
}


install_storlets() {
    echo "Install storlets dependencies"
    prepare_storlets_install

    echo "Install storlets code"
    install_storlets_code

    echo "Configure swift and keystone for storlets"
    configure_swift_and_keystone_for_storlets

    echo "Create Docker images"
    create_base_jre_image
    create_storlet_engine_image
    create_default_tenant_image

    echo "Create test configuration file"
    create_test_config_file

    echo "restart swift"
    _storlets_swift_restart
}

uninstall_storlets() {
    sudo service docker stop
    sudo sed -r 's#^.*DOCKER_OPTS=.*$#DOCKER_OPTS="--debug --storage-opt dm.override_udev_sync_check=true"#' /etc/default/docker

    echo "Cleaning all storlets runtime stuff..."
    sudo rm -fr ${STORLETS_DOCKER_DEVICE}
}
