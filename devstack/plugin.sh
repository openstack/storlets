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

SWIFT_CONF_DIR=${SWIFT_CONF_DIR:-/etc/swift}

# Storlets install tunables
STORLETS_DEFAULT_USER_DOMAIN_ID=${STORLETS_DEFAULT_USER_DOMAIN_ID:-default}
STORLETS_DEFAULT_PROJECT_DOMAIN_ID=${STORLETS_DEFAULT_PROJECT_DOMAIN_ID:-default}
STORLETS_DOCKER_DEVICE=${STORLETS_DOCKER_DEVICE:-/var/lib/storlets}
if is_fedora; then
    STORLETS_DOCKER_BASE_IMG=${STORLETS_DOCKER_BASE_IMG:-quay.io/centos/centos:stream9}
else
    STORLETS_DOCKER_BASE_IMG=${STORLETS_DOCKER_BASE_IMG:-ubuntu:22.04}
fi
STORLETS_SWIFT_RUNTIME_USER=${STORLETS_SWIFT_RUNTIME_USER:-$USER}
STORLETS_SWIFT_RUNTIME_GROUP=${STORLETS_SWIFT_RUNTIME_GROUP:-$USER}
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
    _modify_swift_conf
    _generate_gateway_conf

    # Create storlet related containers and set ACLs
    start_swift
    _export_swift_os_vars
    openstack object store account set --property Storlet-Enabled=True
    swift post --read-acl $SWIFT_DEFAULT_PROJECT:$SWIFT_MEMBER_USER $STORLETS_STORLET_CONTAINER_NAME
    swift post --read-acl $SWIFT_DEFAULT_PROJECT:$SWIFT_MEMBER_USER $STORLETS_DEPENDENCY_CONTAINER_NAME
    swift post $STORLETS_LOG_CONTAIER_NAME
}

function _install_docker {
    if is_fedora; then
        # NOTE(tkajinam): install_docker.sh requires the yum command
        sudo dnf install -y yum
    fi
    wget http://get.docker.com -O install_docker.sh
    chmod 755 install_docker.sh
    sudo bash -x install_docker.sh
    rm install_docker.sh

    # Add swift user to docker group so that the user can manage docker
    # containers without sudo
    sudo grep -q docker /etc/group
    if [ $? -ne 0 ]; then
        sudo groupadd docker
    fi
    add_user_to_group $STORLETS_SWIFT_RUNTIME_USER docker

    # Ensure docker daemon is started
    start_service docker
    if [ $STORLETS_SWIFT_RUNTIME_USER == $USER ]; then
        # NOTE(takashi): We need this workaround because we can't reload
        #                user-group relationship in bash scripts
        DOCKER_UNIX_SOCKET=/var/run/docker.sock
        sudo chown $USER:$USER $DOCKER_UNIX_SOCKET
    fi
}

function prepare_storlets_install {
    _install_docker

    if is_fedora; then
        install_package java-${STORLETS_JDK_VERSION}-openjdk-devel ant
        install_package python3 python3-devel
    else
        install_package openjdk-${STORLETS_JDK_VERSION}-jdk-headless ant
        install_package python3 python3-dev
    fi
}

function _generate_jre_dockerfile {
    if is_fedora; then
        JDK_PACKAGE="java-${STORLETS_JDK_VERSION}-openjdk-headless"
        PYTHON_PACKAGES="python3"
        cat <<EOF > ${TMP_REGISTRY_PREFIX}/repositories/storlet_engine_image/Dockerfile
FROM $STORLETS_DOCKER_BASE_IMG
MAINTAINER root
RUN dnf install ${PYTHON_PACKAGES} ${JDK_PACKAGE} util-linux-core -y && \
    dnf clean all
EOF
    else
        JDK_PACKAGE="openjdk-${STORLETS_JDK_VERSION}-jdk-headless"
        PYTHON_PACKAGES="python3 python3.10"
        cat <<EOF > ${TMP_REGISTRY_PREFIX}/repositories/storlet_engine_image/Dockerfile
FROM $STORLETS_DOCKER_BASE_IMG
MAINTAINER root
RUN apt-get update && \
    apt-get install ${PYTHON_PACKAGES} ${JDK_PACKAGE} -y && \
    apt-get clean
EOF
    fi
}

function create_base_jre_image {
    echo "Create base jre image"
    sudo docker pull $STORLETS_DOCKER_BASE_IMG
    mkdir -p ${TMP_REGISTRY_PREFIX}/repositories/storlet_engine_image
    _generate_jre_dockerfile
    cd ${TMP_REGISTRY_PREFIX}/repositories/storlet_engine_image
    sudo docker build -t storlet_engine_image .
    cd -
}

function create_logback_xml {
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
    sudo mkdir -p -m 755 /usr/local/libexec/storlets
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

function _modify_swift_conf {
    local swift_proxy_config
    swift_proxy_config=${SWIFT_CONF_DIR}/proxy-server.conf
    iniset ${swift_proxy_config} "filter:storlet_handler" use "egg:storlets#storlet_handler"
    iniset ${swift_proxy_config} "filter:storlet_handler" execution_server proxy
    iniset ${swift_proxy_config} "filter:storlet_handler" storlet_container $STORLETS_STORLET_CONTAINER_NAME
    iniset ${swift_proxy_config} "filter:storlet_handler" storlet_dependency $STORLETS_DEPENDENCY_CONTAINER_NAME
    iniset ${swift_proxy_config} "filter:storlet_handler" storlet_log $STORLETS_LOG_CONTAIER_NAME
    iniset ${swift_proxy_config} "filter:storlet_handler" storlet_gateway_module $STORLETS_GATEWAY_MODULE
    iniset ${swift_proxy_config} "filter:storlet_handler" storlet_gateway_conf $STORLETS_GATEWAY_CONF_FILE
    iniset ${swift_proxy_config} "filter:storlet_handler" storlet_execute_on_proxy_only $STORLETS_PROXY_EXECUTION_ONLY

    local proxy_pipeline
    proxy_pipeline=$(iniget ${swift_proxy_config} "pipeline:main" pipeline)
    if ! [[ "${proxy_pipeline}" =~ " storlet_handler copy " ]]; then
        proxy_pipeline=$(echo "${proxy_pipeline}" | sed "s/ copy / storlet_handler copy /")
        iniset ${swift_proxy_config} "pipeline:main" pipeline "${proxy_pipeline}"
    fi

    local node_number
    for node_number in ${SWIFT_REPLICAS_SEQ}; do
        local swift_obj_config
        local obj_pipeline

        swift_obj_config=${SWIFT_CONF_DIR}/object-server/${node_number}.conf
        obj_pipeline=$(iniget ${swift_obj_config} "pipeline:main" pipeline)
        if ! [[ "${obj_pipeline}" =~ " storlet_handler object-server$" ]]; then
            obj_pipeline=$(echo "${obj_pipeline}" | sed "s/ object-server$/ storlet_handler object-server/")
            iniset ${swift_obj_config} "pipeline:main" pipeline "${obj_pipeline}"
        fi

        iniset ${swift_obj_config} "filter:storlet_handler" use "egg:storlets#storlet_handler"
        iniset ${swift_obj_config} "filter:storlet_handler" execution_server object
        iniset ${swift_obj_config} "filter:storlet_handler" storlet_container $STORLETS_STORLET_CONTAINER_NAME
        iniset ${swift_obj_config} "filter:storlet_handler" storlet_dependency $STORLETS_DEPENDENCY_CONTAINER_NAME
        iniset ${swift_obj_config} "filter:storlet_handler" storlet_log $STORLETS_LOG_CONTAIER_NAME
        iniset ${swift_obj_config} "filter:storlet_handler" storlet_gateway_module $STORLETS_GATEWAY_MODULE
        iniset ${swift_obj_config} "filter:storlet_handler" storlet_gateway_conf $STORLETS_GATEWAY_CONF_FILE
        iniset ${swift_obj_config} "filter:storlet_handler" storlet_execute_on_proxy_only $STORLETS_PROXY_EXECUTION_ONLY
    done
}

function _generate_gateway_conf {
    iniset ${STORLETS_GATEWAY_CONF_FILE} DEFAULT storlet_logcontainer $STORLETS_LOG_CONTAIER_NAME
    iniset ${STORLETS_GATEWAY_CONF_FILE} DEFAULT cache_dir $STORLETS_CACHE_DIR
    iniset ${STORLETS_GATEWAY_CONF_FILE} DEFAULT log_dir $STORLETS_LOGS_DIR
    iniset ${STORLETS_GATEWAY_CONF_FILE} DEFAULT script_dir $STORLETS_SCRIPTS_DIR
    iniset ${STORLETS_GATEWAY_CONF_FILE} DEFAULT storlets_dir $STORLETS_STORLETS_DIR
    iniset ${STORLETS_GATEWAY_CONF_FILE} DEFAULT pipes_dir $STORLETS_PIPES_DIR
    iniset ${STORLETS_GATEWAY_CONF_FILE} DEFAULT restart_linux_container_timeout $STORLETS_RESTART_CONTAINER_TIMEOUT
    iniset ${STORLETS_GATEWAY_CONF_FILE} DEFAULT storlet_timeout $STORLETS_RUNTIME_TIMEOUT
}

function _generate_default_tenant_dockerfile {
    cat <<EOF > ${TMP_REGISTRY_PREFIX}/repositories/"$SWIFT_DEFAULT_PROJECT_ID"/Dockerfile
FROM storlet_engine_image
MAINTAINER root
EOF
}

function create_default_tenant_image {
    SWIFT_DEFAULT_PROJECT_ID=`openstack project list | grep -w $SWIFT_DEFAULT_PROJECT | awk '{ print $2 }'`
    mkdir -p ${TMP_REGISTRY_PREFIX}/repositories/$SWIFT_DEFAULT_PROJECT_ID
    _generate_default_tenant_dockerfile
    cd ${TMP_REGISTRY_PREFIX}/repositories/$SWIFT_DEFAULT_PROJECT_ID
    sudo docker build -t ${SWIFT_DEFAULT_PROJECT_ID:0:13} .
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
    create_default_tenant_image

    echo "Create logback xml file"
    create_logback_xml

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
    # TODO(tkajinam): Remove config options
    # TODO(tkajinam): Remove docker containers/images
}

# Restore xtrace
$_XTRACE_LIB_STORLETS

# Tell emacs to use shell-script-mode
## Local variables:
## mode: shell-script
## End:
