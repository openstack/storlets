#! /usr/bin/python

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

import argparse
import json


class Inventory(object):

    '''
    Ansible inventory , generated from config file
    '''
    def __init__(self, fname):
        self.__load_config__(fname)

    def __load_config__(self, name):
        with open(name) as f:
            self.conf = json.loads(f.read())

    def show_list(self):
        g = {}
        for group in ['storlet-mgmt', 'storlet-proxy', 'storlet-storage',
                      'docker']:
            g[group] = dict()
            g[group]['hosts'] = self.conf['groups'][group]
            g[group]['vars'] = dict()
            g[group]['vars'].update(self.conf['all'])
        return g

    def show_host(self, name):
        res = dict()
        res['ansible_ssh_user'] = self.conf['all']['ansible_ssh_user']
        return res


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--host')
    args = parser.parse_args()
    inventory = Inventory('deploy/cluster_config.json')
    out = {}
    if args.list:
        out = inventory.show_list()

    if args.host:
        out = inventory.show_host(args.host)

    print(json.dumps(out))

if __name__ == '__main__':
    main()
