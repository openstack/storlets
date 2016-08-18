'''-------------------------------------------------------------------------
Copyright IBM Corp. 2015, 2016 All Rights Reserved
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
Limitations under the License.
-------------------------------------------------------------------------'''

'''
*VERY* initial cluster configuration file
The intention is to have this as the single source
for all cluster information needs such as:
- Swift Install
- Storlets Install
- Tests
- Deploy storlets tools
- etc.
'''
import json


class ClusterConfig(object):

    def __init__(self, config_path):
        conf_string = open(config_path, 'r').read()
        self.conf = json.loads(conf_string)
        self._auth_version = '2.0'

    # TODO(eran) get rid of returning raw conf
    def get_conf(self):
        return self.conf

    @property
    def auth_uri(self):
        return self.conf['all']['keystone_public_url']

    @property
    def tenant_name(self):
        return self.conf['all']['storlets_default_tenant_name']

    @property
    def user(self):
        return self.conf['all']['storlets_default_tenant_user_name']

    @property
    def password(self):
        return self.conf['all']['storlets_default_tenant_user_password']

    @property
    def region(self):
        return self.conf['all'].get('region', '')

    # TODO(eranr) move to cluster_config
    @property
    def auth_version(self):
        return self._auth_version
