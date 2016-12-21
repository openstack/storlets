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

import unittest
from swiftclient import client as swiftclient
from storlets.tools.cluster_config_parser import ClusterConfig
from storlets.tools.utils import deploy_storlet, get_admin_auth, put_local_file

CONFIG_FILE = '../../cluster_config.json'
PATH_TO_STORLETS = '../../StorletSamples'


class StorletBaseFunctionalTest(unittest.TestCase):
    def setUp(self):
        self.conf_file = CONFIG_FILE
        self.conf = ClusterConfig(CONFIG_FILE)
        self.url, self.token = get_admin_auth(self.conf)
        super(StorletBaseFunctionalTest, self).setUp()


class StorletFunctionalTest(StorletBaseFunctionalTest):

    def create_container(self, container):
        response = dict()
        swiftclient.put_container(self.url, self.token,
                                  container, headers=None,
                                  response_dict=response)
        status = response.get('status')
        assert (status >= 200 or status < 300)

    def setUp(self, language, path_to_bundle,
              storlet_dir,
              storlet_name, storlet_main,
              container, storlet_file,
              dep_names, headers):
        super(StorletFunctionalTest, self).setUp()
        self.storlet_dir = storlet_dir
        self.storlet_name = storlet_name
        self.storlet_main = storlet_main
        self.dep_names = dep_names
        self.path_to_bundle = path_to_bundle
        self.container = container
        self.storlet_file = storlet_file
        self.headers = headers or {}
        self.acct = self.url.split('/')[4]
        self.deps = []
        if dep_names:
            for d in self.dep_names:
                self.deps.append('%s/%s' % (self.path_to_bundle, d))
        storlet = '%s/%s' % (self.path_to_bundle, self.storlet_name)

        deploy_storlet(self.url, self.token,
                       storlet, self.storlet_main,
                       self.deps, language)

        self.create_container(self.container)
        if self.storlet_file:
            put_local_file(self.url, self.token,
                           self.container,
                           self.path_to_bundle,
                           self.storlet_file,
                           self.headers)
