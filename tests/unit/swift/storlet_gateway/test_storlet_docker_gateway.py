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

from tests.unit.swift import FakeLogger
from storlet_gateway.storlet_docker_gateway import StorletGatewayDocker
from swift.common.swob import HTTPException, Request, Response
import unittest


class FakeApp(object):
    def __call__(self, env, start_response):
        req = Request(env)
        return Response(request=req, body='FAKE APP')(
            env, start_response)


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
            'storlet_dependency': 'dependency'
        }
        self.logger = FakeLogger()

    def tearDown(self):
        pass

    def assertRaisesWithStatus(self, status, f, *args, **kwargs):
        try:
            f(*args, **kwargs)
        except HTTPException as e:
            self.assertEqual(e.status_int, status)
        else:
            self.fail("HTTPException is not raised")

    def test_validate_mandatory_headers_for_storlet(self):
        a = 'AUTH_xxxxxxxxxxxxxxxxxxxx'
        c = 'storlet'
        o = 'storlet-1.0.jar'
        path = '/'.join(['/v1', a, c, o])
        gw = StorletGatewayDocker(self.sconf, self.logger, FakeApp(), 'v1',
                                  a, c, o)

        # sufficient headers
        headers = {'x-object-meta-storlet-language': 'java',
                   'x-object-meta-storlet-interface-version': '1.0',
                   'x-object-meta-storlet-dependency': 'dep_file',
                   'x-object-meta-storlet-object-metadata': 'no',
                   'x-object-meta-storlet-main': 'path.to.storlet.class'}
        req = Request.blank(path, environ={'REQUEST_METHOD': 'PUT'},
                            headers=headers)
        gw._validate_mandatory_headers(req)

        # insufficient headers
        headers = {'x-object-meta-storlet-language': 'java',
                   'x-object-meta-storlet-interface-version': '1.0',
                   'x-object-meta-storlet-dependency': 'dep_file',
                   'x-object-meta-storlet-object-metadata': 'no'}
        req = Request.blank(path, environ={'REQUEST_METHOD': 'PUT'},
                            headers=headers)
        self.assertRaisesWithStatus(400, gw._validate_mandatory_headers, req)

    def test_validate_mandatory_headers_for_dependency(self):
        a = 'AUTH_xxxxxxxxxxxxxxxxxxxx'
        c = 'dependency'
        o = 'dep_file'
        path = '/'.join(['/v1', a, c, o])
        gw = StorletGatewayDocker(self.sconf, self.logger, FakeApp(), 'v1',
                                  a, c, o)

        # sufficient headers
        headers = {'x-object-meta-storlet-dependency-version': '1.0'}
        req = Request.blank(path, environ={'REQUEST_METHOD': 'PUT'},
                            headers=headers)
        gw._validate_mandatory_headers(req)

        # insufficient headers
        headers = {}
        req = Request.blank(path, environ={'REQUEST_METHOD': 'PUT'},
                            headers=headers)
        self.assertRaisesWithStatus(400, gw._validate_mandatory_headers, req)

    def test_validate_storlet_upload(self):
        a = 'AUTH_xxxxxxxxxxxxxxxxxxxx'
        c = self.sconf['storlet_container']

        # correct name
        o = 'storlet-1.0.jar'
        path = '/'.join(['/v1', a, c, o])
        req = Request.blank(path, environ={'REQUEST_METHOD': 'PUT'})
        gw = StorletGatewayDocker(self.sconf, self.logger, FakeApp(), 'v1',
                                  a, c, o)
        gw._validate_storlet_upload(req)

        # wrong name
        o = 'storlet.jar'
        path = '/'.join(['/v1', a, c, o])
        req = Request.blank(path, environ={'REQUEST_METHOD': 'PUT'})
        gw = StorletGatewayDocker(self.sconf, self.logger, FakeApp(), 'v1',
                                  a, c, o)
        self.assertRaisesWithStatus(400, gw._validate_storlet_upload, req)

    def test_validate_dependency_upload(self):
        a = 'AUTH_xxxxxxxxxxxxxxxxxxxx'
        c = self.sconf['storlet_dependency']
        o = 'dep_file'
        path = '/'.join(['/v1', a, c, o])

        # w/o dependency parameter
        req = Request.blank(path, environ={'REQUEST_METHOD': 'PUT'})
        gw = StorletGatewayDocker(self.sconf, self.logger, FakeApp(), 'v1',
                                  a, c, o)
        gw._validate_dependency_upload(req)

        # w/ correct dependency parameter
        req = Request.blank(
            path,
            environ={'REQUEST_METHOD': 'PUT'},
            headers={'x-object-meta-storlet-dependency-permissions': '755'})
        gw = StorletGatewayDocker(self.sconf, self.logger, FakeApp(), 'v1',
                                  a, c, o)
        gw._validate_dependency_upload(req)

        # w/ wrong dependency parameter
        req = Request.blank(
            path,
            environ={'REQUEST_METHOD': 'PUT'},
            headers={'x-object-meta-storlet-dependency-permissions': '400'})
        gw = StorletGatewayDocker(self.sconf, self.logger, FakeApp(), 'v1',
                                  a, c, o)
        self.assertRaisesWithStatus(400, gw._validate_dependency_upload, req)

        # w/ invalid dependency parameter
        req = Request.blank(
            path,
            environ={'REQUEST_METHOD': 'PUT'},
            headers={'x-object-meta-storlet-dependency-permissions': 'foo'})
        gw = StorletGatewayDocker(self.sconf, self.logger, FakeApp(), 'v1',
                                  a, c, o)
        self.assertRaisesWithStatus(400, gw._validate_dependency_upload, req)

        req = Request.blank(
            path,
            environ={'REQUEST_METHOD': 'PUT'},
            headers={'x-object-meta-storlet-dependency-permissions': '888'})
        gw = StorletGatewayDocker(self.sconf, self.logger, FakeApp(), 'v1',
                                  a, c, o)
        self.assertRaisesWithStatus(400, gw._validate_dependency_upload, req)

    def test_authorizeStorletExecution(self):
        a = 'a'
        c = 'c'
        o = 'o'
        so = 'storlets-1.0.jar'
        path = '/'.join(['/v1', a, c, o])

        sheaders = {
            'X-Object-Meta-Storlet-Language': 'java',
            'X-Object-Meta-Storlet-Interface-Version': '1.0',
            'X-Object-Meta-Storlet-Dependency': 'dep_file',
            'X-Object-Meta-Storlet-Object-Metadata': 'no'}

        class FakeApp200(object):
            def __call__(self, env, start_response):
                req = Request(env)
                return Response(request=req, headers=sheaders)(
                    env, start_response)

        gw = StorletGatewayDocker(self.sconf, self.logger, FakeApp200(), 'v1',
                                  a, c, o)
        env = {'REQUEST_METHOD': 'GET'}
        req = Request.blank(path, environ=env,
                            headers={'X-Run-Storlet': so})
        gw.authorizeStorletExecution(req)
        for key in sheaders.keys():
            self.assertEqual(sheaders[key], gw.storlet_metadata[key])

    def test_verify_access(self):
        a = 'a'
        c = 'c'
        o = 'o'
        sc = self.sconf['storlet_container']
        so = 'storlets-1.0.jar'
        path = '/'.join(['/v1', a, c, o])

        sheaders = {
            'X-Object-Meta-Storlet-Language': 'java',
            'X-Object-Meta-Storlet-Interface-Version': '1.0',
            'X-Object-Meta-Storlet-Dependency': 'dep_file',
            'X-Object-Meta-Storlet-Object-Metadata': 'no'}

        class FakeApp200(object):
            def __call__(self, env, start_response):
                req = Request(env)
                return Response(request=req, headers=sheaders)(
                    env, start_response)

        gw = StorletGatewayDocker(self.sconf, self.logger, FakeApp200(), 'v1',
                                  a, c, o)
        env = {'REQUEST_METHOD': 'GET'}
        req = Request.blank(path, environ=env,
                            headers={'X-Run-Storlet': so})
        headers = gw._verify_access(req, 'v1', a, sc, so)
        for key in sheaders.keys():
            self.assertEqual(sheaders[key], headers[key])

        class FakeApp401(object):
            def __call__(self, env, start_response):
                req = Request(env)
                return Response(request=req, status='401 Unauthorized')(
                    env, start_response)

        gw = StorletGatewayDocker(self.sconf, self.logger, FakeApp401(), 'v1',
                                  a, c, o)
        env = {'REQUEST_METHOD': 'GET'}
        req = Request.blank(path, environ=env,
                            headers={'X-Run-Storlet': so})
        self.assertRaisesWithStatus(401, gw._verify_access, req, 'v1',
                                    a, sc, so)

        class FakeApp404(object):
            def __call__(self, env, start_response):
                req = Request(env)
                return Response(request=req, status='404 Not Found')(
                    env, start_response)

        gw = StorletGatewayDocker(self.sconf, self.logger, FakeApp404(), 'v1',
                                  a, c, o)
        env = {'REQUEST_METHOD': 'GET'}
        req = Request.blank(path, environ=env,
                            headers={'X-Run-Storlet': so})
        self.assertRaisesWithStatus(401, gw._verify_access, req, 'v1',
                                    a, sc, so)


if __name__ == '__main__':
    unittest.main()
