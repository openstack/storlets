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
from swift.common.swob import HTTPException, HTTPNoContent, \
    HTTPUnauthorized, HTTPNotFound, Request
from tests.unit.swift import FakeLogger
from tests.unit.swift.storlet_middleware import FakeApp
from storlet_gateway.storlet_docker_gateway import DockerStorletRequest, \
    StorletGatewayDocker


class TestDockerStorletRequest(unittest.TestCase):

    def test_init(self):
        account = 'a'
        headers = {'X-Object-Meta-Storlet-Main': 'main',
                   'X-Storlet-Key0': 'Value0',
                   'x-storlet-key1': 'Value1',
                   'X-Object-Meta-Storlet-Key2': 'Value2',
                   'x-object-meta-storlet-key3': 'Value3',
                   'X-Object-Meta-Key4': 'Value4',
                   'x-object-meta-key5': 'Value5'}
        params = {'Param6': 'Value6',
                  'Param7': 'Value7'}
        req = Request.blank('', headers=headers)
        dsreq = DockerStorletRequest(account, req, params)

        self.assertEqual(dsreq.generate_log, False)
        self.assertEqual(dsreq.storlet_id, 'main')
        self.assertEqual(dsreq.user_metadata,
                         {'Key4': 'Value4',
                          'Key5': 'Value5'})
        self.assertEqual(dsreq.account, account)


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
            self.sconf, self.logger, self.app,
            self.version, self.account, self.container, self.obj)

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

    def test_validate_mandatory_headers(self):
        self.container = self.storlet_container
        headers = {'keyA': 'valueA',
                   'keyB': 'valueB',
                   'keyC': 'valueC'}
        req = self._create_req('PUT', headers=headers)
        gw = self._create_gateway()

        # all mandatory headers are included
        gw._validate_mandatory_headers(req, ['keyA', 'keyB'])

        # some of mandatory headers are missing
        with self.assertRaisesHttpStatus(400):
            gw._validate_mandatory_headers(req, ['keyA', 'KeyD'])

    def test_validate_storlet_upload(self):
        self.container = self.storlet_container

        # correct name and headers
        self.obj = 'storlet-1.0.jar'
        headers = {'x-object-meta-storlet-language': 'java',
                   'x-object-meta-storlet-interface-version': '1.0',
                   'x-object-meta-storlet-dependency': 'dep_file',
                   'x-object-meta-storlet-object-metadata': 'no',
                   'x-object-meta-storlet-main': 'path.to.storlet.class'}
        req = self._create_req('PUT', headers=headers)
        gw = self._create_gateway()
        gw._validate_storlet_upload(req)

        # some header keys are missing
        self.obj = 'storlet-1.0.jar'
        headers = {'x-object-meta-storlet-language': 'java',
                   'x-object-meta-storlet-interface-version': '1.0',
                   'x-object-meta-storlet-dependency': 'dep_file',
                   'x-object-meta-storlet-object-metadata': 'no'}
        req = self._create_req('PUT', headers=headers)
        gw = self._create_gateway()
        with self.assertRaisesHttpStatus(400):
            gw._validate_storlet_upload(req)

        # wrong name
        self.obj = 'storlet.jar'
        req = self._create_req('PUT', headers=headers)
        gw = self._create_gateway()
        with self.assertRaisesHttpStatus(400):
            gw._validate_storlet_upload(req)

    def test_validate_dependency_upload(self):
        self.container = self.storlet_dependency

        # w/o dependency parameter
        headers = {'x-object-meta-storlet-dependency-version': '1.0'}
        req = self._create_req('PUT', headers=headers)
        gw = self._create_gateway()
        gw._validate_dependency_upload(req)

        # w/ correct dependency parameter
        headers = {
            'x-object-meta-storlet-dependency-permissions': '755',
            'x-object-meta-storlet-dependency-version': '1.0'}
        req = self._create_req('PUT', headers=headers)
        gw = self._create_gateway()
        gw._validate_dependency_upload(req)

        # w/ wrong dependency parameter
        headers = {
            'x-object-meta-storlet-dependency-permissions': '400',
            'x-object-meta-storlet-dependency-version': '1.0'}
        req = self._create_req('PUT', headers=headers)
        gw = self._create_gateway()
        with self.assertRaisesHttpStatus(400):
            gw._validate_dependency_upload(req)

        # w/ invalid dependency parameter
        headers = {
            'x-object-meta-storlet-dependency-permissions': 'foo',
            'x-object-meta-storlet-dependency-version': '1.0'}
        req = self._create_req('PUT', headers=headers)
        gw = self._create_gateway()
        with self.assertRaisesHttpStatus(400):
            gw._validate_dependency_upload(req)

        headers = {
            'x-object-meta-storlet-dependency-permissions': '888',
            'x-object-meta-storlet-dependency-version': '1.0'}
        req = self._create_req('PUT', headers=headers)
        gw = self._create_gateway()
        with self.assertRaisesHttpStatus(400):
            gw._validate_dependency_upload(req)

    def test_authorizeStorletExecution(self):
        sheaders = {
            'X-Object-Meta-Storlet-Language': 'java',
            'X-Object-Meta-Storlet-Interface-Version': '1.0',
            'X-Object-Meta-Storlet-Dependency': 'dep_file',
            'X-Object-Meta-Storlet-Object-Metadata': 'no'}
        self.app.register('HEAD', self.storlet_path, HTTPNoContent, sheaders)
        gw = self._create_gateway()
        req = self._create_storlet_req('GET')
        gw.authorizeStorletExecution(req)
        for key in sheaders.keys():
            self.assertEqual(sheaders[key], gw.storlet_metadata[key])
        self.assertEqual(len(self.app.get_calls()), 1)

    def test_augmentStorletExcecution(self):
        # Metadata specific to Storlet
        sheaders = {
            'X-Object-Meta-Storlet-Language': 'java',
            'X-Object-Meta-Storlet-Interface-Version': '1.0',
            'X-Object-Meta-Storlet-Dependency': 'dep_file',
            'X-Object-Meta-Storlet-Object-Metadata': 'no'}

        # Normal Metadata about object
        oheaders = {'X-Timestamp': '1450000000.000',
                    'Content-Length': '1024',
                    'X-Object-Meta-Key': 'Value'}
        oheaders.update(sheaders)

        self.app.register('HEAD', self.storlet_path, HTTPNoContent, oheaders)
        gw = self._create_gateway()
        req = self._create_storlet_req('GET')

        # Set storlet_metadata
        gw.authorizeStorletExecution(req)

        gw.augmentStorletRequest(req)

        for key in sheaders:
            self.assertEqual(req.headers[key], sheaders[key])
        self.assertEqual(req.headers['X-Storlet-X-Timestamp'],
                         '1450000000.000')
        self.assertEqual(req.headers['X-Storlet-Content-Length'],
                         '1024')

    def test_verify_access(self):
        sheaders = {
            'X-Object-Meta-Storlet-Language': 'java',
            'X-Object-Meta-Storlet-Interface-Version': '1.0',
            'X-Object-Meta-Storlet-Dependency': 'dep_file',
            'X-Object-Meta-Storlet-Object-Metadata': 'no'}

        # If we get 204 when heading storlet object
        self.app.register('HEAD', self.storlet_path, HTTPNoContent, sheaders)
        gw = self._create_gateway()
        req = self._create_storlet_req('GET')
        headers = gw._verify_access(req, self.version, self.account,
                                    self.storlet_container, self.sobj)
        for key in sheaders.keys():
            self.assertEqual(sheaders[key], headers[key])
        self.assertEqual(len(self.app.get_calls()), 1)
        self.app.reset_all()

        # If we get 401 when heading storlet object
        self.app.register('HEAD', self.storlet_path, HTTPUnauthorized)
        gw = self._create_gateway()
        req = self._create_storlet_req('GET')
        with self.assertRaisesHttpStatus(401):
            gw._verify_access(req, self.version, self.account,
                              self.storlet_container, self.sobj)
        self.assertEqual(len(self.app.get_calls()), 1)
        self.app.reset_all()

        # If we get 404 when heading storlet object
        self.app.register('HEAD', self.storlet_path, HTTPNotFound)
        gw = self._create_gateway()
        req = self._create_storlet_req('GET')
        with self.assertRaisesHttpStatus(401):
            gw._verify_access(req, self.version, self.account,
                              self.storlet_container, self.sobj)
        self.assertEqual(len(self.app.get_calls()), 1)

    def test_clean_storlet_stuff_from_request(self):
        headers = {'X-Storlet-Key1': 'Value1',
                   'X-Key2': 'Value2',
                   'X-Object-Meta-Storlet-Key3': 'Value3',
                   'X-Object-Meta-Key4': 'Value4'}
        req = self._create_req('GET', headers=headers)
        gw = self._create_gateway()
        gw._clean_storlet_stuff_from_request(req.headers)

        self.assertFalse('X-Storlet-Key1' in req.headers)
        self.assertEqual(req.headers['X-Key2'], 'Value2')
        self.assertFalse('X-Object-Meta-Storlet-Key3' in req.headers)
        self.assertEqual(req.headers['X-Object-Meta-Key4'], 'Value4')

    def test_set_metadata_in_headers(self):
        gw = self._create_gateway()

        headers = {'HeaderKey1': 'HeaderValue1'}
        gw._set_metadata_in_headers(headers, {})
        self.assertEqual(headers, {'HeaderKey1': 'HeaderValue1'})

        md = {'MetaKey1': 'MetaValue1'}
        gw._set_metadata_in_headers(headers, md)
        self.assertEqual(headers,
                         {'HeaderKey1': 'HeaderValue1',
                          'X-Object-Meta-MetaKey1': 'MetaValue1'})


if __name__ == '__main__':
    unittest.main()
