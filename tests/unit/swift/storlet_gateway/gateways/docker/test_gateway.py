# Copyright (c) 2010-2015 OpenStack Foundation
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

from contextlib import contextmanager
import unittest
from six import StringIO
from swift.common.swob import HTTPException, Request
from tests.unit.swift import FakeLogger
from tests.unit.swift.storlet_middleware import FakeApp
from storlet_gateway.gateways.docker.gateway import DockerStorletRequest, \
    StorletGatewayDocker


class TestDockerStorletRequest(unittest.TestCase):

    def test_init(self):
        storlet_id = 'Storlet-1.0.jar'
        params = {'Param1': 'Value1', 'Param2': 'Value2'}
        metadata = {'MetaKey1': 'MetaValue1', 'MetaKey2': 'MetaValue2'}
        options = {'storlet_main': 'org.openstack.storlet.Storlet',
                   'storlet_dependency': 'dep1,dep2'}
        dsreq = DockerStorletRequest(storlet_id, params, metadata,
                                     iter(StringIO()), options=options)

        self.assertEqual(metadata, dsreq.user_metadata)
        self.assertEqual(params, dsreq.params)
        self.assertEqual('Storlet-1.0.jar', dsreq.storlet_id)
        self.assertEqual('org.openstack.storlet.Storlet', dsreq.storlet_main)
        self.assertEqual(['dep1', 'dep2'], dsreq.dependencies)

    def test_init_with_range(self):
        storlet_id = 'Storlet-1.0.jar'
        params = {}
        metadata = {}
        options = {'storlet_main': 'org.openstack.storlet.Storlet',
                   'storlet_dependency': 'dep1,dep2',
                   'range_start': 1,
                   'range_end': 6}
        dsreq = DockerStorletRequest(storlet_id, params, metadata,
                                     None, 0, options=options)

        self.assertEqual('Storlet-1.0.jar', dsreq.storlet_id)
        self.assertEqual('org.openstack.storlet.Storlet', dsreq.storlet_main)
        self.assertEqual(['dep1', 'dep2'], dsreq.dependencies)
        self.assertEqual(1, dsreq.start)
        self.assertEqual(6, dsreq.end)

        options = {'storlet_main': 'org.openstack.storlet.Storlet',
                   'storlet_dependency': 'dep1,dep2',
                   'range_start': 0,
                   'range_end': 0}
        dsreq = DockerStorletRequest(storlet_id, params, metadata,
                                     None, 0, options=options)

        self.assertEqual('Storlet-1.0.jar', dsreq.storlet_id)
        self.assertEqual('org.openstack.storlet.Storlet', dsreq.storlet_main)
        self.assertEqual(['dep1', 'dep2'], dsreq.dependencies)
        self.assertEqual(0, dsreq.start)
        self.assertEqual(0, dsreq.end)

    def test_has_range(self):
        storlet_id = 'Storlet-1.0.jar'
        params = {}
        metadata = {}
        options = {'storlet_main': 'org.openstack.storlet.Storlet',
                   'storlet_dependency': 'dep1,dep2'}
        dsreq = DockerStorletRequest(storlet_id, params, metadata,
                                     None, 0, options=options)
        self.assertFalse(dsreq.has_range)

        options = {'storlet_main': 'org.openstack.storlet.Storlet',
                   'storlet_dependency': 'dep1,dep2',
                   'range_start': 1,
                   'range_end': 6}
        dsreq = DockerStorletRequest(storlet_id, params, metadata,
                                     None, 0, options=options)
        self.assertTrue(dsreq.has_range)

        options = {'storlet_main': 'org.openstack.storlet.Storlet',
                   'storlet_dependency': 'dep1,dep2',
                   'range_start': 0,
                   'range_end': 6}
        dsreq = DockerStorletRequest(storlet_id, params, metadata,
                                     None, 0, options=options)
        self.assertTrue(dsreq.has_range)


class TestStorletGatewayDocker(unittest.TestCase):

    def setUp(self):
        # TODO(takashi): take these values from config file
        self.sconf = {
            'lxc_root': '/home/docker_device/scopes',
            'cache_dir': '/home/docker_device/cache/scopes',
            'log_dir': '/home/docker_device/logs/scopes',
            'script_dir': '/home/docker_device/scripts',
            'storlets_dir': '/home/docker_device/storlets/scopes',
            'pipes_dir': '/home/docker_device/pipes/scopes',
            'storlet_timeout': '9',
            'storlet_container': 'storlet',
            'storlet_dependency': 'dependency',
            'reseller_prefix': 'AUTH'
        }
        self.logger = FakeLogger()
        self.app = FakeApp()

        self.storlet_container = self.sconf['storlet_container']
        self.storlet_dependency = self.sconf['storlet_dependency']

        self.version = 'v1'
        self.account = 'a'
        self.container = 'c'
        self.obj = 'o'
        self.sobj = 'storlet-1.0.jar'

    @property
    def req_path(self):
        return self._create_proxy_path(
            self.version, self.account, self.container,
            self.obj)

    @property
    def storlet_path(self):
        return self._create_proxy_path(
            self.version, self.account, self.storlet_container,
            self.sobj)

    def tearDown(self):
        pass

    def _create_gateway(self):
        return StorletGatewayDocker(
            self.sconf, self.logger, self.app, self.account)

    def _create_proxy_path(self, version, account, container, obj):
        return '/'.join(['', version, account, container, obj])

    def _create_req(self, method, headers=None, body=None):
        return Request.blank(
            self.req_path, environ={'REQUEST_METHOD': method},
            headers=headers, body=body)

    def _create_storlet_req(self, method, headers=None, body=None):
        if headers is None:
            headers = {}
        headers['X-Run-Storlet'] = self.sobj
        return self._create_req(method, headers, body)

    @contextmanager
    def assertRaisesHttpStatus(self, status):
        with self.assertRaises(HTTPException) as e:
            yield
            self.assertEqual(e.status_int, status)

    def test_check_mandatory_params(self):
        params = {'keyA': 'valueA',
                  'keyB': 'valueB',
                  'keyC': 'valueC'}

        # all mandatory headers are included
        StorletGatewayDocker._check_mandatory_params(
            params, ['keyA', 'keyB'])

        # some of mandatory headers are missing
        with self.assertRaises(ValueError):
            StorletGatewayDocker._check_mandatory_params(
                params, ['keyA', 'KeyD'])

    def test_validate_storlet_registration(self):
        # correct name and headers
        obj = 'storlet-1.0.jar'
        params = {'Language': 'java',
                  'Interface-Version': '1.0',
                  'Dependency': 'dep_file',
                  'Object-Metadata': 'no',
                  'Main': 'path.to.storlet.class'}
        StorletGatewayDocker.validate_storlet_registration(params, obj)

        # some header keys are missing
        params = {'Language': 'java',
                  'Interface-Version': '1.0',
                  'Dependency': 'dep_file',
                  'Object-Metadata': 'no'}
        with self.assertRaises(ValueError):
            StorletGatewayDocker.validate_storlet_registration(params, obj)

        # wrong name
        obj = 'storlet.jar'
        params = {'Language': 'java',
                  'Interface-Version': '1.0',
                  'Dependency': 'dep_file',
                  'Object-Metadata': 'no',
                  'Main': 'path.to.storlet.class'}
        with self.assertRaises(ValueError):
            StorletGatewayDocker.validate_storlet_registration(params, obj)

        # unsupported language
        obj = 'storlet.foo'
        params = {'Language': 'bar',
                  'Interface-Version': '1.0',
                  'Dependency': 'dep_file',
                  'Object-Metadata': 'no',
                  'Main': 'path.to.storlet.class'}
        with self.assertRaises(ValueError):
            StorletGatewayDocker.validate_storlet_registration(params, obj)

    def test_validate_dependency_registration(self):
        # w/o dependency parameter
        obj = 'dep_file'
        params = {'Dependency-Version': '1.0'}
        StorletGatewayDocker.validate_dependency_registration(params, obj)

        # w/ correct dependency parameter
        params = {
            'Dependency-Permissions': '755',
            'Dependency-Version': '1.0'}
        StorletGatewayDocker.validate_dependency_registration(params, obj)

        # w/ wrong dependency parameter
        params = {
            'Dependency-Permissions': '400',
            'Dependency-Version': '1.0'}
        with self.assertRaises(ValueError):
            StorletGatewayDocker.validate_dependency_registration(params, obj)

        # w/ invalid dependency parameter
        params = {
            'Dependency-Permissions': 'foo',
            'Dependency-Version': '1.0'}
        with self.assertRaises(ValueError):
            StorletGatewayDocker.validate_dependency_registration(params, obj)

        params = {
            'Dependency-Permissions': '888',
            'Dependency-Version': '1.0'}
        with self.assertRaises(ValueError):
            StorletGatewayDocker.validate_dependency_registration(params, obj)

if __name__ == '__main__':
    unittest.main()
