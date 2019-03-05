# Copyright IBM Corp. 2015, 2015 All Rights Reserved
# Copyright (c) 2010-2016 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from swiftclient import client


def put_local_file(url, token, container, local_dir, local_file, headers=None):
    """
    Put local file to swift

    :param url: swift endpoint url
    :param token: token string to access to swift
    :param local_dir: directory path where the target file is placed
    :param loca_file: name of the file to be put to swift
    :param headers: headers parameters to be included in request headers
    """
    resp = dict()
    with open(os.path.join(local_dir, local_file), 'r') as f:
        client.put_object(url, token, container, local_file, f,
                          headers=headers,
                          content_type="application/octet-stream",
                          response_dict=resp)
        status = resp.get('status', 0)
        assert (status // 100 == 2)


def put_storlet_object(url, token, storlet, dependencies, storlet_main_class,
                       language='Java', version=None):
    """
    Put storlet file to swift

    :param url: swift endpoint url
    :param token: token string to access to swift
    :param storlet: storlet file to be registerd
    :param dependencies: a list of dependency files
    :param storlet_main_class: name of the storlet main class
    :param language: storlet language. default value is Java
    :param version: storlet language version. defaulte is 2.7 for python
    """
    headers = {'X-Object-Meta-Storlet-Language': language,
               'X-Object-Meta-Storlet-Interface-Version': '1.0',
               'X-Object-Meta-Storlet-Object-Metadata': 'no',
               'X-Object-Meta-Storlet-Main': storlet_main_class}
    if dependencies:
        headers['X-Object-Meta-Storlet-Dependency'] = dependencies
    if version and language.lower() == 'python':
        headers['X-Object-Meta-Storlet-Language-Version'] = version

    put_local_file(url, token, 'storlet', os.path.dirname(storlet),
                   os.path.basename(storlet), headers)


def put_storlet_executable_dependencies(url, token, deps):
    """
    Put dependency files to swift with 755 permission

    :param url: swift endpoint url:
    :param token: token swring to access to swift
    :param deps: a list of dependency files to be registered
    """
    for dep in deps:
        headers = {'X-Object-Meta-Storlet-Dependency-Version': '1',
                   'X-Object-Meta-Storlet-Dependency-Permissions': '0755'}
        put_local_file(url, token, 'dependency', os.path.dirname(dep),
                       os.path.basename(dep), headers)


def deploy_storlet(url, token, storlet, storlet_main_class, dependencies,
                   language='Java', version=None):
    """
    Deploy storlet file and required dependencies as swift objects

    :param url: swift endpoint url
    :param token: token string to access swift
    :param storlet: storlet file to be registerd
    :param dependencies: a list of dependency files to be registered
    :param language: storlet language. default value is Java
    :param version: storlet language version. defaulte is 2.7 for python
    """
    # No need to create containers every time
    # put_storlet_containers(url, token)
    put_storlet_object(url, token, storlet,
                       ','.join(os.path.basename(x) for x in dependencies),
                       storlet_main_class, language, version)

    put_storlet_executable_dependencies(url, token, dependencies)


def get_auth(conf, user, passwd):
    """
    Get token string to access to swift

    :param conf: a dict of config parameters
    :returns: (swift endpoint url, token string)
    """
    auth_url = conf.auth_uri
    project = conf.project_name
    os_options = {'user_domain_name': conf.domain_name,
                  'project_name': conf.project_name,
                  'region_name': conf.region}
    url, token = client.get_auth(auth_url, project + ':' + user, passwd,
                                 os_options=os_options,
                                 auth_version=conf.auth_version)
    return url, token


def get_admin_auth(conf):
    admin_user = conf.admin_user
    admin_passwd = conf.admin_password
    return get_auth(conf, admin_user, admin_passwd)


def get_member_auth(conf):
    member_user = conf.member_user
    member_passd = conf.member_password
    return get_auth(conf, member_user, member_passd)
