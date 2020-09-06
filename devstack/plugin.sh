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
_XTRACE_LIB_STORLETS=$(set +o | grep xtrace)
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
STORLETS_DOCKER_DEVICE=${STORLETS_DOCKER_DEVICE:-/home/docker_device}
STORLETS_DOCKER_BASE_IMG=${STORLETS_DOCKER_BASE_IMG:-ubuntu:20.04}
STORLETS_DOCKER_BASE_IMG_NAME=${STORLETS_DOCKER_BASE_IMG_NAME:-ubuntu_20.04}
STORLETS_DOCKER_SWIFT_GROUP_ID=${STORLETS_DOCKER_SWIFT_GROUP_ID:-1003}
STORLETS_DOCKER_SWIFT_USER_ID=${STORLETS_DOCKER_SWIFT_USER_ID:-1003}
STORLETS_SWIFT_RUNTIME_USER=${STORLETS_SWIFT_RUNTIME_USER:-$USER}
STORLETS_SWIFT_RUNTIME_GROUP=${STORLETS_SWIFT_RUNTIME_GROUP:-$USER}
STORLETS_MIDDLEWARE_NAME=storlet_handler
STORLETS_STORLET_CONTAINER_NAME=${STORLETS_STORLET_CONTAINER_NAME:-storlet}
STORLETS_DEPENDENCY_CONTAINER_NAME=${STORLETS_DEPENDENCY_CONTAINER_NAME:-dependency}
STORLETS_LOG_CONTAIER_NAME=${STORLETS_LOG_CONTAIER_NAME:-log}
STORLETS_GATEWAY_MODULE=${STORLETS_GATEWAY_MODULE:-docker}
STORLETS_GATEWAY_CONF_FILE=${STORLETS_GATEWAY_CONF_FILE:-${SWIFT_CONF_DIR}/storlet_docker_gateway.conf}
STORLETS_PROXY_EXECUTION_ONLY=${STORLETS_PROXY_EXECUTION_ONLY:-false}
STORLETS_SCRIPTS_DIR=${STORLETS_SCRIPTS_DIR:-"$STORLETS_DOCKER_DEVICE"/scripts}
STORLETS_STORLETS_DIR=${STORLETS_STORLETS_DIR:-"$STORLETS_DOCKER_DEVICE"/storlets/scopes}
STORLETS_LOGS_DIR=${STORLETS_LOGS_DIR:-"$STORLETS_DOCKER_DEVICE"/logs/scopes}
STORLETS_CACHE_DIR=${STORLETS_CACHE_DIR:-"$STORLETS_DOCKER_DEVICE"/cache/scopes}
STORLETS_PIPES_DIR=${STORLETS_PIPES_DIR:-"$STORLETS_DOCKER_DEVICE"/pipes/scopes}
STORLETS_RESTART_CONTAINER_TIMEOUT=${STORLETS_RESTART_CONTAINER_TIMEOUT:-3}
STORLETS_RUNTIME_TIMEOUT=${STORLETS_RUNTIME_TIMEOUT:-40}
STORLETS_JDK_VERSION=${STORLETS_JDK_VERSION:-11}

TMP_REGISTRY_PREFIX=/tmp/registry

# Functions
# ---------

function _export_os_vars {
    export OS_IDENTITY_API_VERSION=3
    export OS_AUTH_URL="http://$KEYSTONE_IP/identity/v3"
    export OS_REGION_NAME=RegionOne
}

function _export_keystone_os_vars {
    _export_os_vars
    export OS_USERNAME=$ADMIN_USER
    export OS_USER_DOMAIN_ID=$STORLETS_DEFAULT_USER_DOMAIN_ID
    export OS_PASSWORD=$ADMIN_PASSWORD
    export OS_PROJECT_NAME=$ADMIN_USER
    export OS_PROJECT_DOMAIN_ID=$STORLETS_DEFAULT_PROJECT_DOMAIN_ID
}

function _export_swift_os_vars {
    _export_os_vars
    export OS_USERNAME=$SWIFT_DEFAULT_USER
    export OS_USER_DOMAIN_ID=$STORLETS_DEFAULT_USER_DOMAIN_ID
    export OS_PASSWORD=$SWIFT_DEFAULT_USER_PWD
    export OS_PROJECT_NAME=$SWIFT_DEFAULT_PROJECT
    export OS_PROJECT_DOMAIN_ID=$STORLETS_DEFAULT_PROJECT_DOMAIN_ID
}

function configure_swift_and_keystone_for_storlets {
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

    if [ "${USE_PYTHON3}" == "False" ]; then
        sudo python2 devstack/swift_config.py install /tmp/swift_middleware_conf $STORLETS_SWIFT_RUNTIME_USER
    else
        sudo python3 devstack/swift_config.py install /tmp/swift_middleware_conf $STORLETS_SWIFT_RUNTIME_USER
    fi

    rm /tmp/swift_middleware_conf
    rm /tmp/storlet-docker-gateway.conf

    # Create storlet related containers and set ACLs
    start_swift
    _export_swift_os_vars
    openstack object store account set --property Storlet-Enabled=True
    swift post --read-acl $SWIFT_DEFAULT_PROJECT:$SWIFT_MEMBER_USER $STORLETS_STORLET_CONTAINER_NAME
    swift post --read-acl $SWIFT_DEFAULT_PROJECT:$SWIFT_MEMBER_USER $STORLETS_DEPENDENCY_CONTAINER_NAME
    swift post $STORLETS_LOG_CONTAIER_NAME
}

function _install_docker {
    # TODO: Add other dirstors.
    # This one is geared towards Ubuntu
    # See other projects that install docker

    wget http://get.docker.com -O install_docker.sh
    sudo chmod 777 install_docker.sh
    sudo bash -x install_docker.sh
    sudo rm install_docker.sh

    # Add swift user to docker group so that the user can manage docker
    # containers without sudo
    sudo grep -q docker /etc/group
    if [ $? -ne 0 ]; then
      sudo groupadd docker
    fi
    add_user_to_group $STORLETS_SWIFT_RUNTIME_USER docker

    if [ $STORLETS_SWIFT_RUNTIME_USER == $USER ]; then
      # NOTE(takashi): We need this workaroud because we can't reload
      #                user-group relationship in bash scripts
      DOCKER_UNIX_SOCKET=/var/run/docker.sock
      sudo chown $USER:$USER $DOCKER_UNIX_SOCKET
    fi

    # Restart docker daemon
    restart_service docker
}

function prepare_storlets_install {
    _install_docker

    if is_ubuntu; then
      install_package openjdk-${STORLETS_JDK_VERSION}-jdk-headless ant
    else
      die $LINENO "Unsupported distro"
    fi

    if [ "${USE_PYTHON3}" == "False" ]; then
      # TODO(takashi): Remove this when we remove py2 support
      install_package python2.7 python2.7-dev
    else
      install_python3
    fi

}

function _generate_jre_dockerfile {
    # TODO(tkajinam): Remove py2 packages when we remove its support
    local PYTHON_PACKAGES='python2.7 python2.7-dev python3.8 python3.8-dev'
    if python3_enabled; then
        PYTHON_PACKAGES="python2.7 python2.7-dev python${PYTHON3_VERSION} python${PYTHON3_VERSION}-dev"
    fi

    cat <<EOF > ${TMP_REGISTRY_PREFIX}/repositories/${STORLETS_DOCKER_BASE_IMG_NAME}_jre${STORLETS_JDK_VERSION}/Dockerfile
FROM $STORLETS_DOCKER_BASE_IMG
MAINTAINER root

RUN apt-get update && \
    apt-get install ${PYTHON_PACKAGES} openjdk-${STORLETS_JDK_VERSION}-jre-headless -y && \
    apt-get clean
EOF
}

function create_base_jre_image {
    echo "Create base jre image"
    sudo docker pull $STORLETS_DOCKER_BASE_IMG
    mkdir -p ${TMP_REGISTRY_PREFIX}/repositories/"$STORLETS_DOCKER_BASE_IMG_NAME"_jre${STORLETS_JDK_VERSION}
    _generate_jre_dockerfile
    cd ${TMP_REGISTRY_PREFIX}/repositories/"$STORLETS_DOCKER_BASE_IMG_NAME"_jre${STORLETS_JDK_VERSION}
    sudo docker build -q -t ${STORLETS_DOCKER_BASE_IMG_NAME}_jre${STORLETS_JDK_VERSION} .
    cd -
}

function _generate_logback_xml {
    sudo tee /usr/local/lib/storlets/logback.xml <<EOF >/dev/null
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
    sudo chmod 0744 /usr/local/lib/storlets/logback.xml
}

function _generate_jre_storlet_dockerfile {
    cat <<EOF > ${TMP_REGISTRY_PREFIX}/repositories/"$STORLETS_DOCKER_BASE_IMG_NAME"_jre${STORLETS_JDK_VERSION}_storlets/Dockerfile
FROM ${STORLETS_DOCKER_BASE_IMG_NAME}_jre${STORLETS_JDK_VERSION}
MAINTAINER root
RUN [ "groupadd", "-g", "$STORLETS_DOCKER_SWIFT_GROUP_ID", "swift" ]
RUN [ "useradd", "-u" , "$STORLETS_DOCKER_SWIFT_USER_ID", "-g", "$STORLETS_DOCKER_SWIFT_GROUP_ID", "swift" ]

CMD ["prod", "/mnt/channels/factory_pipe", "DEBUG"]

ENTRYPOINT ["/usr/local/libexec/storlets/init_container.sh"]
EOF
}

function create_storlet_engine_image {
    echo "Create Storlet engine image"
    mkdir -p ${TMP_REGISTRY_PREFIX}/repositories/"$STORLETS_DOCKER_BASE_IMG_NAME"_jre${STORLETS_JDK_VERSION}_storlets
    _generate_logback_xml
    _generate_jre_storlet_dockerfile
    cd ${TMP_REGISTRY_PREFIX}/repositories/"$STORLETS_DOCKER_BASE_IMG_NAME"_jre${STORLETS_JDK_VERSION}_storlets
    sudo docker build -q -t ${STORLETS_DOCKER_BASE_IMG_NAME}_jre${STORLETS_JDK_VERSION}_storlets .
    cd -
}

function install_storlets_code {
    echo "Installing storlets"
    cd $REPO_DIR
    sudo ./install_libs.sh
    pip_install .

    # install test requirements because we still need some packages in the list
    # to prepare deployment
    pip_install -r ./test-requirements.txt

    # Also install code to library directory so that we can import them
    # from docker container.
    sudo mkdir -p -m 755 /usr/local/lib/storlets/python

    # NOTE(takashi): We need --no-deps to avoid enum34 installed in py 2 env,
    #                which causes failure in py3 execution.
    pip_install . -t /usr/local/lib/storlets/python --no-compile --no-deps
    for bin_file in storlets-daemon storlets-daemon-factory ; do
        sudo cp `which ${bin_file}` /usr/local/libexec/storlets/
    done

    sudo mkdir -p -m 0755 $STORLETS_DOCKER_DEVICE
    sudo chown -R "$STORLETS_SWIFT_RUNTIME_USER":"$STORLETS_SWIFT_RUNTIME_GROUP" $STORLETS_DOCKER_DEVICE

    # NOTE(takashi): We should cleanup egg-info directory here, otherwise it
    #                causes permission denined when installing package by tox.
    sudo rm -rf storlets.egg-info

    cd -
}

function _generate_swift_middleware_conf {
    cat <<EOF > /tmp/swift_middleware_conf
[proxy-confs]
proxy_server_conf_file = ${SWIFT_CONF_DIR}/proxy-server.conf
storlet_proxy_server_conf_file = ${SWIFT_CONF_DIR}/storlet-proxy-server.conf

[object-confs]
object_server_conf_files = ${SWIFT_CONF_DIR}/object-server/1.conf

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

function _generate_storlet-docker-gateway {
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

function _generate_default_tenant_dockerfile {
    cat <<EOF > ${TMP_REGISTRY_PREFIX}/repositories/"$SWIFT_DEFAULT_PROJECT_ID"/Dockerfile
FROM ${STORLETS_DOCKER_BASE_IMG_NAME}_jre${STORLETS_JDK_VERSION}_storlets
MAINTAINER root
EOF
}

function create_default_tenant_image {
    SWIFT_DEFAULT_PROJECT_ID=`openstack project list | grep -w $SWIFT_DEFAULT_PROJECT | awk '{ print $2 }'`
    mkdir -p ${TMP_REGISTRY_PREFIX}/repositories/$SWIFT_DEFAULT_PROJECT_ID
    _generate_default_tenant_dockerfile
    cd ${TMP_REGISTRY_PREFIX}/repositories/$SWIFT_DEFAULT_PROJECT_ID
    sudo docker build -q -t ${SWIFT_DEFAULT_PROJECT_ID:0:13} .
    cd -
}

function create_test_config_file {
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

function install_storlets {
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
    stop_swift
    start_swift
}

function uninstall_storlets {
    sudo service docker stop

    echo "Cleaning all storlets runtime stuff..."
    sudo rm -fr ${STORLETS_DOCKER_DEVICE}
}

# Restore xtrace
$_XTRACE_LIB_STORLETS

# Tell emacs to use shell-script-mode
## Local variables:
## mode: shell-script
## End:
