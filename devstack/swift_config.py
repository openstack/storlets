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

import ConfigParser
import fileinput
import os
import pwd
import shutil
import sys

swift_run_time_user = None


def _chown_to_swift(path):
    global swift_run_time_user
    uc = pwd.getpwnam(swift_run_time_user)
    os.chown(path, uc.pw_uid, uc.pw_gid)


def _unpatch_pipeline_line(orig_line, storlet_middleware):
    mds = list()
    for md in orig_line.split():
        if md == 'pipeline' or md == '=':
            continue
        mds.append(md)

    if storlet_middleware in mds:
        mds.remove(storlet_middleware)

    new_line = 'pipeline ='
    for md in mds:
        new_line += ' ' + md

    return new_line + '\n'


def _patch_proxy_pipeline_line(orig_line, storlet_middleware):
    mds = list()
    for md in orig_line.split():
        if md == 'pipeline' or md == '=':
            continue
        mds.append(md)

    if storlet_middleware in mds:
        return orig_line

    # If there is 'copy' middleware, storlet_hander is placed
    # in the left of 'copy' middleware.
    try:
        copy_index = mds.index('copy')
    except Exception:
        copy_index = -1

    if copy_index != -1:
        mds.insert(copy_index, storlet_middleware)
    else:
        # If there is slo middleware, storlet_hander is placed
        # in the left of slo middleware.
        try:
            slo_index = mds.index('slo')
        except Exception:
            slo_index = -1

        if slo_index != -1:
            mds.insert(slo_index, storlet_middleware)
        else:
            # Otherwise, storlet_hander is placed in the left of proxy-sever.
            proxy_index = mds.index('proxy-server')
            mds.insert(proxy_index, storlet_middleware)

    new_line = 'pipeline ='
    for md in mds:
        new_line += ' ' + md

    return new_line + '\n'


def _patch_object_pipeline_line(orig_line, storlet_middleware):
    mds = list()
    for md in orig_line.split():
        if md == 'pipeline' or md == '=':
            continue
        mds.append(md)

    if storlet_middleware in mds:
        return orig_line

    object_index = mds.index('object-server')
    mds.insert(object_index, storlet_middleware)

    new_line = 'pipeline ='
    for md in mds:
        new_line += ' ' + md

    return new_line + '\n'


def unpatch_swift_config_file(conf, conf_file):
    storlet_middleware = conf.get('common-confs', 'storlet_middleware')

    for line in fileinput.input(conf_file, inplace=1):
        if line.startswith('pipeline'):
            new_line = _unpatch_pipeline_line(line, storlet_middleware)
            line = new_line
        sys.stdout.write(line)

    _chown_to_swift(conf_file)


def patch_swift_config_file(conf, conf_file, service):
    storlet_middleware = conf.get('common-confs', 'storlet_middleware')
    filter_block_first_line = '[filter:%s]\n' % storlet_middleware

    filter_in_file = False
    for line in fileinput.input(conf_file, inplace=1):
        if line.startswith('pipeline'):
            if service == 'proxy':
                new_line = _patch_proxy_pipeline_line(line, storlet_middleware)
            else:
                new_line = _patch_object_pipeline_line(line,
                                                       storlet_middleware)
            line = new_line
        if filter_block_first_line in line:
            filter_in_file = True
        sys.stdout.write(line)

    if filter_in_file is False:
        with open(conf_file, 'a') as f:
            f.write('\n')
            f.write(filter_block_first_line)
            f.write('use = egg:storlets#%s\n' % storlet_middleware)
            f.write('storlet_container = %s\n' %
                    conf.get('common-confs', 'storlet_container'))
            f.write('storlet_dependency = %s\n' %
                    conf.get('common-confs', 'storlet_dependency'))
            f.write('storlet_gateway_module = %s\n' %
                    conf.get('common-confs', 'storlet_gateway_module'))
            f.write('storlet_gateway_conf = %s\n' %
                    conf.get('common-confs', 'storlet_gateway_conf'))
            f.write('storlet_execute_on_proxy_only = %s\n' % conf.get(
                'common-confs', 'storlet_proxy_execution'))
            f.write('execution_server = %s\n' % service)

    _chown_to_swift(conf_file)


def unpatch_swift_storlet_proxy_file(conf):
    storlet_proxy_server_conf_file = conf.get('proxy-confs',
                                              'storlet_proxy_server_conf_file')
    if os.path.exists(storlet_proxy_server_conf_file):
        os.remove(storlet_proxy_server_conf_file)


def patch_swift_storlet_proxy_file(conf):
    storlet_proxy_server_conf_file = conf.get('proxy-confs',
                                              'storlet_proxy_server_conf_file')
    proxy_server_conf_file = conf.get('proxy-confs', 'proxy_server_conf_file')

    source_file = proxy_server_conf_file
    target_file = storlet_proxy_server_conf_file
    shutil.copyfile(source_file, target_file)

    for line in fileinput.input(storlet_proxy_server_conf_file, inplace=1):
        if line.startswith('pipeline'):
            # If there is no proxy-logging in the configuration file, we don't
            # want to add it to the pipeline. This may cause invalid internal
            # client configuration (we encountered this problem in a fuel swift
            # cluster).
            if 'proxy-logging' in line:
                line = 'pipeline = proxy-logging cache storlet_handler slo ' + \
                       'proxy-logging proxy-server\n'
            else:
                line = 'pipeline = cache storlet_handler slo proxy-server\n'
        sys.stdout.write(line)

    _chown_to_swift(storlet_proxy_server_conf_file)


def remove_gateway_conf_file(conf):
    gateway_conf_file = conf.get('common-confs', 'storlet_gateway_conf')
    if os.path.exists(gateway_conf_file):
        os.remove(gateway_conf_file)


def remove(conf):
    object_server_conf_files = conf.get('object-confs',
                                        'object_server_conf_files').split(',')
    for f in object_server_conf_files:
        if os.path.exists(f):
            unpatch_swift_config_file(conf, f)

    proxy_server_conf_file = conf.get('proxy-confs', 'proxy_server_conf_file')
    unpatch_swift_config_file(conf, proxy_server_conf_file)

    unpatch_swift_storlet_proxy_file(conf)
    remove_gateway_conf_file(conf)


def install(conf):
    object_server_conf_files = conf.get('object-confs',
                                        'object_server_conf_files').split(',')
    for f in object_server_conf_files:
        if os.path.exists(f):
            patch_swift_config_file(conf, f, 'object')

    proxy_server_conf_file = conf.get('proxy-confs', 'proxy_server_conf_file')
    patch_swift_config_file(conf, proxy_server_conf_file, 'proxy')

    patch_swift_storlet_proxy_file(conf)


def usage(argv):
    print("Usage: %s %s %s" % (argv[0],
                               "install/remove conf_file",
                               "swift_run_time_user"))


def main(argv):
    if len(argv) != 4:
        usage(argv)
        exit(-1)

    conf = ConfigParser.ConfigParser()
    conf.read(argv[2])
    global swift_run_time_user
    swift_run_time_user = argv[3]

    if argv[1] == 'install':
        install(conf)
    elif argv[1] == 'remove':
        remove(conf)
    else:
        usage(argv)

if __name__ == "__main__":
    main(sys.argv)
