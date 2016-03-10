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
from common.cluster_config_parser import ClusterConfig
from common.utils import storlet_get_auth, deploy_storlet,\
    put_local_file

CONFIG_FILE = '../../cluster_config.json'
PATH_TO_STORLETS = '../../StorletSamples'
BIN_DIR = 'bin'


class StorletFunctionalTest(unittest.TestCase):
    def setUp(self):
        conf = ClusterConfig(CONFIG_FILE).get_conf()
        self.url, self.token = storlet_get_auth(conf)
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
        if self.storlet_file:
            put_local_file(self.url, self.token,
                           self.container,
                           self.path_to_bundle,
                           self.storlet_file,
                           self.headers)
