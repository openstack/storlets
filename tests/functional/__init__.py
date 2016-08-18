'''-------------------------------------------------------------------------
Copyright IBM Corp. 2015, 2015 All Rights Reserved
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

import unittest
from tools.cluster_config_parser import ClusterConfig
from tools.utils import get_auth, deploy_storlet,\
    put_local_file
from swiftclient import client as swiftclient

CONFIG_FILE = '../../cluster_config.json'
PATH_TO_STORLETS = '../../StorletSamples'
BIN_DIR = 'bin'


class StorletBaseFunctionalTest(unittest.TestCase):
    def setUp(self):
        self.conf_file = CONFIG_FILE
        self.conf = ClusterConfig(CONFIG_FILE)
        self.path_to_storlets = PATH_TO_STORLETS
        self.bin_dir = BIN_DIR
        super(StorletBaseFunctionalTest, self).setUp()


class StorletFunctionalTest(StorletBaseFunctionalTest):

    def create_container(self):
        response = dict()
        swiftclient.put_container(self.url, self.token,
                                  self.container, headers=None,
                                  response_dict=response)
        status = response.get('status')
        assert (status >= 200 or status < 300)

    def setUp(self):
        super(StorletFunctionalTest, self).setUp()
        self.url, self.token = get_auth(self.conf)
        self.acct = self.url.split('/')[4]
        self.path_to_bundle = '%s/%s/%s' % (PATH_TO_STORLETS, self.storlet_dir,
                                            BIN_DIR)
        self.deps = []
        for d in self.dep_names:
            self.deps.append('%s/%s' % (self.path_to_bundle, d))
        storlet = '%s/%s' % (self.path_to_bundle, self.storlet_name)

        deploy_storlet(self.url, self.token,
                       storlet, self.storlet_main,
                       self.deps)
        self.create_container()
        if self.storlet_file:
            put_local_file(self.url, self.token,
                           self.container,
                           self.path_to_bundle,
                           self.storlet_file,
                           self.headers)
