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

import copy
import mock
from os.path import join
from storlet_middleware import storlet_handler
from swift.common.swob import Request
from swift.common.swob import Response
import unittest


# TODO(takashi): take these values from config file
DEFAULT_CONFIG = {
    'storlet_container': 'storlet',
    'storlet_dependency': 'dependency',
    'storlet_timeout': '40',
    'storlet_gateway_module':
        'storlet_gateway.storlet_stub_gateway:StorletGatewayStub',
    'storlet_gateway_conf': '/etc/swift/storlet_stub_gateway.conf',
    'execution_server': 'proxy'}


class TestStorletsHandler(unittest.TestCase):
    def setUp(self):
        self.got_statuses = []
        self.got_headers = []
        self.conf = copy.copy(DEFAULT_CONFIG)

    def tearDown(self):
        pass

    def get_app(self, app, global_conf, **local_conf):
        factory = storlet_handler.filter_factory(global_conf, **local_conf)
        return factory(app)

    def start_response(self, status, headers):
        self.got_statuses.append(status)
        self.got_headers.append(headers)

    # TODO(takashi): We don't have to run this test for base class
    def test_load_app(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                req = Request(env)
                return Response(body='FAKE APP', request=req)(
                    env, start_response)

        try:
            self.get_app(FakeApp(), self.conf)
        except Exception:
            self.fail('Application loading got an error')


class TestStorletHandlerProxy(TestStorletsHandler):
    def setUp(self):
        super(TestStorletHandlerProxy, self).setUp()
        self.conf['execution_server'] = 'proxy'

    def test_GET_without_storlets(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                req = Request(env)
                return Response(body='FAKE APP', request=req)(
                    env, start_response)

        def basic_get(path):
            req = Request.blank(path, environ={'REQUEST_METHOD': 'GET'})
            app = self.get_app(FakeApp(), self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['FAKE APP'])

        for target in ('AUTH_a', 'AUTH_a/c', 'AUTH_a/c/o'):
            path = join('/', 'v1', target)
            basic_get(path)

    def test_GET_with_storlets(self):
        class FakeApp(object):
            def __init__(self):
                self.called_requests = []

            def __call__(self, env, start_response):
                req = Request(env)
                self.called_requests.append(req)
                # TODO(kota->takashi): This will be needed after refactor
                # because, right now, we can not test the existence HEAD
                # request with stub gateway. In my idea, we could move the
                # validation from gateway into handler in storlet_middleware
                # if req.path == '/v1/AUTH_a/storlets/Storlet-1.0.jar':
                #     return Response(request=req)(
                #         env, start_response)
                if req.path == '/v1/AUTH_a/c/o':
                    return Response(body='FAKE RESULT', request=req)(
                        env, start_response)
                else:
                    raise Exception('Request for unexpected path')

        def get(path):
            req = Request.blank(path, environ={'REQUEST_METHOD': 'GET'},
                                headers={'X-Run-Storlet': 'Storlet-1.0.jar'})
            fake_app = FakeApp()
            app = self.get_app(fake_app, self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['FAKE RESULT'])
            # The last one is exexution GET call
            self.assertEqual('/v1/AUTH_a/c/o',
                             fake_app.called_requests[-1].path)
            self.assertIn('X-Run-Storlet',
                          fake_app.called_requests[-1].headers)
            # TODO(takashi): This will be needed after refactor like as above
            # Previous one is confirmation for jar file
            # self.assertEqual('/v1/AUTH_a/storlet/storlet-1.0.jar',
            #                  fake_app.called_requests[-2].path)
            # self.assertNotIn('X-Run-Storlet',
            #                  fake_app.called_requests[-2].headers)

        def get_fake_account_meta(*args, **kwargs):
            return {'meta': {'storlet-enabled': 'true'}}

        with mock.patch('storlet_middleware.storlet_handler.get_account_info',
                        get_fake_account_meta):
            get('/v1/AUTH_a/c/o')

    def test_GET_with_storlets_disabled_account(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                raise Exception('Request for unexpected path')

        def get(path):
            req = Request.blank(path, environ={'REQUEST_METHOD': 'GET'},
                                headers={'X-Run-Storlet': 'Storlet-1.0.jar'})
            app = self.get_app(FakeApp(), self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('400 Bad Request', self.got_statuses[-1])

        def get_fake_account_meta(*args, **kwargs):
            return {'meta': {}}

        with mock.patch('storlet_middleware.storlet_handler.get_account_info',
                        get_fake_account_meta):
            get('/v1/AUTH_a/c/o')

    def test_GET_with_storlets_object_404(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                req = Request(env)
                if req.path == '/v1/AUTH_a/storlets/Storlet-1.0.jar':
                    return Response(status='200 OK', request=req)(
                        env, start_response)
                elif req.path == '/v1/AUTH_a/c/o':
                    return Response(status='404 Not Found', request=req)(
                        env, start_response)
                else:
                    raise Exception('Request for unexpected path')

        def get(path):
            req = Request.blank(path, environ={'REQUEST_METHOD': 'GET'},
                                headers={'X-Run-Storlet': 'Storlet-1.0.jar'})
            app = self.get_app(FakeApp(), self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('404 Not Found', self.got_statuses[-1])

        def get_fake_account_meta(*args, **kwargs):
            return {'meta': {'storlet-enabled': 'true'}}

        with mock.patch('storlet_middleware.storlet_handler.get_account_info',
                        get_fake_account_meta):
            get('/v1/AUTH_a/c/o')

    def test_GET_slo_without_storlets(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                req = Request(env)
                if req.path == '/v1/AUTH_a/c/slo_manifest':
                    return Response(
                        body='FAKE APP',
                        headers={'x-static-large-object': 'True'},
                        request=req)(
                        env, start_response)
                else:
                    raise Exception('Request for unexpected path')

        def get(path):
            req = Request.blank(path, environ={'REQUEST_METHOD': 'GET'})
            app = self.get_app(FakeApp(), self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual(resp, ['FAKE APP'])

        def get_fake_account_meta(*args, **kwargs):
            return {'meta': {}}

        with mock.patch('storlet_middleware.storlet_handler.get_account_info',
                        get_fake_account_meta):
            get('/v1/AUTH_a/c/slo_manifest')

    def test_GET_slo_with_storlets(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                req = Request(env)
                if req.path == '/v1/AUTH_a/c/slo_manifest':
                    return Response(
                        body='FAKE APP',
                        headers={'x-static-large-object': 'True'},
                        request=req)(
                        env, start_response)
                else:
                    raise Exception('Request for unexpected path')

        def get(path):
            req = Request.blank(path, environ={'REQUEST_METHOD': 'GET'},
                                headers={'X-Run-Storlet': 'Storlet-1.0.jar'})
            app = self.get_app(FakeApp(), self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual(resp, ['DUMMY_CONTENT'])

        def get_fake_account_meta(*args, **kwargs):
            return {'meta': {'storlet-enabled': 'true'}}

        with mock.patch('storlet_middleware.storlet_handler.get_account_info',
                        get_fake_account_meta):
            get('/v1/AUTH_a/c/slo_manifest')

    def test_PUT_without_storlets(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                req = Request(env)
                return Response(status='201 Created', request=req)(
                    env, start_response)

        called = [0]

        def mock_authorizeStorletExecution(req):
            called[0] += 1

        def basic_put(path):
            req = Request.blank(path, environ={'REQUEST_METHOD': 'PUT'})
            app = self.get_app(FakeApp(), self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('201 Created', self.got_statuses[-1])

        with mock.patch(
                'storlet_gateway.storlet_stub_gateway.StorletGatewayStub.'
                'authorizeStorletExecution',
                mock_authorizeStorletExecution):
            for target in ('AUTH_a', 'AUTH_a/c', 'AUTH_a/c/o'):
                path = join('/', 'v1', target)
                basic_put(path)
            self.assertEqual(0, called[0])

    def test_PUT_with_storlets(self):
        class FakeApp(object):
            def __init__(self):
                self.req_body = []

            def __call__(self, env, start_response):
                req = Request(env)
                if req.path == '/v1/AUTH_a/c/o':
                    self.req_body.append(req.body_file)
                    return Response(status='201 Created', request=req)(
                        env, start_response)
                else:
                    raise Exception('Request for unexpected path')

        def put(path):
            req = Request.blank(path, environ={'REQUEST_METHOD': 'PUT'},
                                headers={'X-Run-Storlet': 'Storlet-1.0.jar'},
                                body='FAKE APP')
            fapp = FakeApp()
            app = self.get_app(fapp, self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('201 Created', self.got_statuses[-1])
            self.assertEqual(['DUMMY_CONTENT'], fapp.req_body[-1])

        def get_fake_account_meta(*args, **kwargs):
            return {'meta': {'storlet-enabled': 'true'}}

        with mock.patch('storlet_middleware.storlet_handler.'
                        'get_account_info',
                        get_fake_account_meta):
            put('/v1/AUTH_a/c/o')

    def test_PUT_storlet(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                req = Request(env)
                return Response(status='201 Created', request=req)(
                    env, start_response)

        def put(path):
            sheaders = {'X-Object-Meta-Storlet-Language': 'Java',
                        'X-Object-Meta-Storlet-Interface-Version': '1.0',
                        'X-Object-Meta-Storlet-Dependency': 'dependency',
                        'X-Object-Meta-Storlet-Main':
                            'org.openstack.storlet.Storlet'}
            req = Request.blank(path, environ={'REQUEST_METHOD': 'PUT'},
                                headers=sheaders)
            app = self.get_app(FakeApp(), self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('201 Created', self.got_statuses[-1])

        def get_fake_account_meta(*args, **kwargs):
            return {'meta': {'storlet-enabled': 'true'}}

        with mock.patch('storlet_middleware.storlet_handler.get_account_info',
                        get_fake_account_meta):
            put('/v1/AUTH_a/storlet/storlet-1.0.jar')

    def test_GET_storlet(self):
        sheaders = {'X-Object-Meta-Storlet-Language': 'Java',
                    'X-Object-Meta-Storlet-Interface-Version': '1.0',
                    'X-Object-Meta-Storlet-Dependency': 'dependency',
                    'X-Object-Meta-Storlet-Main':
                        'org.openstack.storlet.Storlet'}

        class FakeApp(object):
            def __call__(self, env, start_response):
                req = Request(env)
                return Response(request=req, headers=sheaders,
                                body='FAKE APP')(
                    env, start_response)

        def get(path):
            req = Request.blank(path, environ={'REQUEST_METHOD': 'GET'})
            app = self.get_app(FakeApp(), self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['FAKE APP'])
            resp_headers = dict(self.got_headers[-1])
            for key in sheaders:
                self.assertEqual(resp_headers[key], sheaders[key])

        def get_fake_account_meta(*args, **kwargs):
            return {'meta': {'storlet-enabled': 'true'}}

        with mock.patch('storlet_middleware.storlet_handler.get_account_info',
                        get_fake_account_meta):
            get('/v1/AUTH_a/storlet/storlet-1.0.jar')

    def test_PUT_dependency(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                req = Request(env)
                return Response(status='201 Created', request=req)(
                    env, start_response)

        def put(path):
            sheaders = {'X-Object-Meta-Storlet-Dependency-Version': '1',
                        'X-Object-Meta-Storlet-Dependency-Permissions': '0755'}
            req = Request.blank(path, environ={'REQUEST_METHOD': 'PUT'},
                                headers=sheaders)
            app = self.get_app(FakeApp(), self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('201 Created', self.got_statuses[-1])

        def get_fake_account_meta(*args, **kwargs):
            return {'meta': {'storlet-enabled': 'true'}}

        with mock.patch('storlet_middleware.storlet_handler.get_account_info',
                        get_fake_account_meta):
            put('/v1/AUTH_a/dependency/dependency')

    def test_GET_dependency(self):
        sheaders = {'X-Object-Meta-Storlet-Dependency-Version': '1',
                    'X-Object-Meta-Storlet-Dependency-Permissions': '0755'}

        class FakeApp(object):
            def __call__(self, env, start_response):
                req = Request(env)
                return Response(request=req, headers=sheaders,
                                body='FAKE APP')(
                    env, start_response)

        def get(path):
            req = Request.blank(path, environ={'REQUEST_METHOD': 'PUT'})
            app = self.get_app(FakeApp(), self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['FAKE APP'])
            resp_headers = dict(self.got_headers[-1])
            for key in sheaders:
                self.assertEqual(resp_headers[key], sheaders[key])

        def get_fake_account_meta(*args, **kwargs):
            return {'meta': {'storlet-enabled': 'true'}}

        with mock.patch('storlet_middleware.storlet_handler.get_account_info',
                        get_fake_account_meta):
            get('/v1/AUTH_a/dependency/dependency')


class TestStorletHandlerObject(TestStorletsHandler):
    def setUp(self):
        super(TestStorletHandlerObject, self).setUp()
        self.conf['execution_server'] = 'object'

    def test_call_unsupported_method(self):
        def call(method):
            path = '/sda1/p/AUTH_a/c/o'
            headers = {'X-Backend-Storlet-Policy-Index': '0',
                       'X-Run-Storlet': 'Storlet-1.0.jar'}
            req = Request.blank(path, environ={'REQUEST_METHOD': method},
                                headers=headers)
            app = self.get_app(lambda env, start: None, self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('405 Method Not Allowed', self.got_statuses[-1])

        for method in ('POST', 'PUT', 'DELETE'):
            call(method)

    def test_PUT_objet_into_storlets_container(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                req = Request(env)
                return Response(status='201 Created', request=req)(
                    env, start_response)

        def put(path):
            sheaders = {'X-Object-Meta-Storlet-Language': 'Java',
                        'X-Object-Meta-Storlet-Interface-Version': '1.0',
                        'X-Object-Meta-Storlet-Dependency': 'dependency',
                        'X-Object-Meta-Storlet-Main':
                            'org.openstack.storlet.Storlet'}
            req = Request.blank(path, environ={'REQUEST_METHOD': 'PUT'},
                                headers=sheaders)
            app = self.get_app(FakeApp(), self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('201 Created', self.got_statuses[-1])

        put('/sda1/p/AUTH_a/storlet/storlet-1.0.jar')

    def test_GET_without_storlets(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                req = Request(env)
                return Response(request=req, body='FAKE APP')(
                    env, start_response)

        def basic_get(path):
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'},
                headers={'X-Backend-Storlet-Policy-Index': '0'})
            app = self.get_app(FakeApp(), self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['FAKE APP'])

        basic_get('/sda1/p/AUTH_a/c/o')

    def test_GET_with_storlets(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                req = Request(env)
                return Response(request=req, body='FAKE APP')(
                    env, start_response)

        def get(path):
            print(self.conf['execution_server'])
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'},
                headers={'X-Backend-Storlet-Policy-Index': '0',
                         'X-Run-Storlet': 'Storlet-1.0.jar'})
            app = self.get_app(FakeApp(), self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['DUMMY_CONTENT'])

        get('/sda1/p/AUTH_a/c/o')

    def test_GET_slo_manifest_with_storlets(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                req = Request(env)
                return Response(
                    request=req,
                    headers={'X-Static-Large-Object': 'True'},
                    body='FAKE MANIFEST')(
                    env, start_response)

        def get(path):
            print(self.conf['execution_server'])
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'},
                headers={'X-Backend-Storlet-Policy-Index': '0',
                         'X-Run-Storlet': 'Storlet-1.0.jar'})
            app = self.get_app(FakeApp(), self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['FAKE MANIFEST'])

        get('/sda1/p/AUTH_a/c/o')

    def test_GET_slo_segment_with_storlets(self):
        class FakeApp(object):
            def __call__(self, env, start_response):
                req = Request(env)
                return Response(
                    request=req,
                    headers={'X-Static-Large-Object': 'True'},
                    body='FAKE APP')(
                    env, start_response)

        def get(path):
            print(self.conf['execution_server'])
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'},
                headers={'X-Backend-Storlet-Policy-Index': '0',
                         'multipart-manifest': 'get',
                         'X-Run-Storlet': 'Storlet-1.0.jar'})
            app = self.get_app(FakeApp(), self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['FAKE APP'])

        get('/sda1/p/AUTH_a/c/o')


if __name__ == '__main__':
    unittest.main()
