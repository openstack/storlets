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
import uuid

from swiftclient import client as swiftclient
from storlets.tools.cluster_config_parser import ClusterConfig
from storlets.tools.utils import deploy_storlet, get_admin_auth, put_local_file
import os

CONFIG_DIR = os.environ.get('CLUSTER_CONF_DIR', os.getcwd())
CONFIG_FILE = os.path.join(CONFIG_DIR, 'test.conf')
PATH_TO_STORLETS = os.environ.get(
    'STORLET_SAMPLE_PATH',
    # assuming, current working dir is at top of storlet repo
    os.path.join(os.getcwd(), 'StorletSamples'))
CONSOLE_TIMEOUT = 2


class StorletBaseFunctionalTest(unittest.TestCase):
    def setUp(self):
        self.conf_file = CONFIG_FILE
        try:
            self.conf = ClusterConfig(CONFIG_FILE)
        except IOError:
            self.fail('cluster_config.json not found in %s. '
                      'Please check your testing environment.' % CONFIG_DIR)

        self.url, self.token = get_admin_auth(self.conf)
        # TODO(kota_): do we need to call setUp() when inheriting TestCase
        # directly? AFAIK, no setUp method in the class...
        super(StorletBaseFunctionalTest, self).setUp()


class StorletFunctionalTest(StorletBaseFunctionalTest):

    def create_container(self, container):
        response = dict()
        swiftclient.put_container(self.url, self.token,
                                  container, headers=None,
                                  response_dict=response)
        status = response.get('status')
        assert (status >= 200 or status < 300)

    def cleanup_container(self, container):
        # list all objects inside the container
        _, objects = swiftclient.get_container(
            self.url, self.token, container, full_listing=True)

        # delete all objects inside the container
        # N.B. this cleanup could run in parallel but currently we have a few
        # objects in the user testing container so that, currently this does
        # as sequential simply
        for obj_dict in objects:
            swiftclient.delete_object(
                self.url, self.token, container, obj_dict['name'])
        swiftclient.get_container(self.url, self.token, container)

        # delete the container
        swiftclient.delete_container(self.url, self.token, container)

    def setUp(self, language, path_to_bundle,
              storlet_dir,
              storlet_name, storlet_main, storlet_file,
              dep_names, headers, version=None):
        super(StorletFunctionalTest, self).setUp()
        self.storlet_dir = storlet_dir
        self.storlet_name = storlet_name
        self.storlet_main = storlet_main
        self.dep_names = dep_names
        self.path_to_bundle = path_to_bundle
        self.container = 'container-%s' % uuid.uuid4()
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
                       self.deps, language, version)

        self.create_container(self.container)
        if self.storlet_file:
            put_local_file(self.url, self.token,
                           self.container,
                           self.path_to_bundle,
                           self.storlet_file,
                           self.headers)

    def tearDown(self):
        self.cleanup_container(self.container)
