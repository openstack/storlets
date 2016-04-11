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
import unittest

from contextlib import contextmanager
from swift.common.swob import Request, HTTPOk, HTTPCreated, HTTPAccepted, \
    HTTPBadRequest, HTTPNotFound
from storlet_middleware import storlet_handler
from storlet_middleware.storlet_handler import StorletProxyHandler, \
    StorletObjectHandler, BaseStorletHandler

from tests.unit.swift import FakeLogger
from tests.unit.swift.storlet_middleware import FakeApp


# TODO(takashi): take these values from config file
DEFAULT_CONFIG = {
    'storlet_container': 'storlet',
    'storlet_dependency': 'dependency',
    'storlet_timeout': '40',
    'storlet_gateway_module':
        'storlet_gateway.storlet_stub_gateway:StorletGatewayStub',
    'storlet_gateway_conf': '/etc/swift/storlet_stub_gateway.conf',
    'execution_server': 'proxy'}


class TestStorletMiddleware(unittest.TestCase):
    def setUp(self):
        self.got_statuses = []
        self.got_headers = []
        self.conf = copy.copy(DEFAULT_CONFIG)
        self.app = FakeApp()

    def tearDown(self):
        pass

    def get_app(self, app, global_conf, **local_conf):
        with mock.patch('storlet_middleware.storlet_handler.get_logger') as \
            get_fake_logger:
            get_fake_logger.return_value = FakeLogger()
            factory = storlet_handler.filter_factory(global_conf, **local_conf)
        return factory(app)

    def start_response(self, status, headers):
        self.got_statuses.append(status)
        self.got_headers.append(headers)

    # TODO(takashi): We don't have to run this test for base class
    def test_load_app(self):
        try:
            self.get_app(self.app, self.conf)
        except Exception:
            self.fail('Application loading got an error')


@contextmanager
def fake_acc_info(acc_info):
    with mock.patch('storlet_middleware.storlet_handler.'
                    'get_account_info') as ai:
        ai.return_value = acc_info
        yield


@contextmanager
def storlet_enabled():
    acc_info = {'meta': {'storlet-enabled': 'true'}}
    with fake_acc_info(acc_info):
        yield


@contextmanager
def authorize_storlet_execution():
    with mock.patch(
            'storlet_gateway.storlet_stub_gateway.StorletGatewayStub.'
            'authorizeStorletExecution') as ase:
        yield ase


class TestStorletMiddlewareProxy(TestStorletMiddleware):
    def setUp(self):
        super(TestStorletMiddlewareProxy, self).setUp()
        self.conf['execution_server'] = 'proxy'

    def test_GET_without_storlets(self):
        def basic_get(path):
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'})
            self.app.register('GET', path, HTTPOk, body='FAKE APP')
            app = self.get_app(self.app, self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['FAKE APP'])
            self.app.reset_all()

        for target in ('AUTH_a', 'AUTH_a/c', 'AUTH_a/c/o'):
            path = '/'.join(['', 'v1', target])
            basic_get(path)

    def test_GET_with_storlets(self):
        # TODO(takashi): decide request path based on config value
        target = '/v1/AUTH_a/c/o'
        self.app.register('GET', target, HTTPOk, body='FAKE RESULT')
        # TODO(kota->takashi): This will be needed after refactor
        # because, right now, we can not test the existence HEAD
        # request with stub gateway. In my idea, we could move the
        # validation from gateway into handler in storlet_middleware
        # storlet = '/v1/AUTH_a/storlet/Storlet-1.0.jar'
        # self.app.register('GET', storlet, HTTPOk, body='jar binary')

        def get(path):
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'},
                headers={'X-Run-Storlet': 'Storlet-1.0.jar'})
            app = self.get_app(self.app, self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['FAKE RESULT'])
            # The last one is exexution GET call
            self.assertEqual(target,
                             self.app.get_calls()[-1][1])
            self.assertIn('X-Run-Storlet',
                          self.app.get_calls()[-1][2])
            # TODO(takashi): This will be needed after refactor like as above
            # Previous one is confirmation for jar file
            # self.assertEqual(target,
            #                  self.app.get_calls()[-2][1])
            # self.assertIn('X-Run-Storlet',
            #               self.app.get_calls()[-2][2])

        acc_info = {'meta': {'storlet-enabled': 'true'}}
        with fake_acc_info(acc_info):
            get(target)

    def test_GET_with_storlets_disabled_account(self):
        def get(path):
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'},
                headers={'X-Run-Storlet': 'Storlet-1.0.jar'})
            app = self.get_app(self.app, self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('400 Bad Request', self.got_statuses[-1])

        acc_info = {'meta': {}}
        with fake_acc_info(acc_info):
            get('/v1/AUTH_a/c/o')

    def test_GET_with_storlets_object_404(self):
        target = '/v1/AUTH_a/c/o'
        self.app.register('GET', target, HTTPNotFound)
        # TODO(takashi): should uncomment this after refactoring
        # storlet = '/v1/AUTH_a/storlets/Storlet-1.0.jar'
        # self.app.register('GET', storlet, HTTPOk, body='jar binary')

        def get(path):
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'},
                headers={'X-Run-Storlet': 'Storlet-1.0.jar'})
            app = self.get_app(self.app, self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('404 Not Found', self.got_statuses[-1])

        with storlet_enabled():
            get(target)

    def test_GET_with_storlets_and_http_range(self):
        target = '/v1/AUTH_a/c/o'

        def get(path):
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'},
                headers={'X-Run-Storlet': 'Storlet-1.0.jar',
                         'Range': 'bytes=10-20'})
            app = self.get_app(self.app, self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('400 Bad Request', self.got_statuses[-1])

        with storlet_enabled():
            get(target)

    def test_GET_with_storlets_and_storlet_range(self):
        target = '/v1/AUTH_a/c/o'
        self.app.register('GET', target, HTTPOk, body='FAKE APP')

        def get(path):
            req_range = 'bytes=1-6'
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'},
                headers={'X-Run-Storlet': 'Storlet-1.0.jar',
                         'X-Storlet-Range': req_range})
            app = self.get_app(self.app, self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp.read(), 'AKE AP')

            resp_headers = dict(self.got_headers[-1])
            self.assertFalse('Content-Range' in resp_headers)
            self.assertEqual(resp_headers['Storlet-Input-Range'],
                             'bytes 1-6/8')

            raw_req = self.app.get_calls('GET', path)[0]
            for key in ['Range', 'X-Storlet-Range']:
                self.assertEqual(raw_req[2][key], req_range)

        with storlet_enabled():
            get(target)

    def test_GET_slo_without_storlets(self):
        target = '/v1/AUTH_a/c/slo_manifest'
        self.app.register('GET', target, HTTPOk,
                          headers={'x-static-large-object': 'True'},
                          body='FAKE APP')

        def get(path):
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'})
            app = self.get_app(self.app, self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual(resp, ['FAKE APP'])

        get(target)

    def test_GET_slo_with_storlets(self):
        target = '/v1/AUTH_a/c/slo_manifest'
        self.app.register('GET', target, HTTPOk,
                          headers={'x-static-large-object': 'True'},
                          body='FAKE APP')
        # TODO(takashi): should uncomment this after refactoring
        # storlet = '/v1/AUTH_a/storlets/Storlet-1.0.jar'
        # self.app.register('GET', storlet, HTTPOk, body='jar binary')

        def get(path):
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'},
                headers={'X-Run-Storlet': 'Storlet-1.0.jar'})
            app = self.get_app(self.app, self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual(resp.read(), 'FAKE APP')

        with storlet_enabled():
            get(target)

    def test_PUT_without_storlets(self):
        def basic_put(path):
            self.app.register('PUT', path, HTTPCreated)
            req = Request.blank(path, environ={'REQUEST_METHOD': 'PUT'})
            app = self.get_app(self.app, self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('201 Created', self.got_statuses[-1])
            self.app.reset_all()

        with authorize_storlet_execution() as ase:
            for target in ('AUTH_a', 'AUTH_a/c', 'AUTH_a/c/o'):
                path = '/'.join(['', 'v1', target])
                basic_put(path)
            self.assertEqual(0, ase.call_count)

    def test_PUT_with_storlets(self):
        target = '/v1/AUTH_a/c/o'
        self.app.register('PUT', target, HTTPCreated)
        # TODO(takashi): should uncomment this after refactoring
        # storlet = '/v1/AUTH_a/storlets/Storlet-1.0.jar'
        # self.app.register('GET', storlet, HTTPOk, 'jar binary')

        def put(path):
            req = Request.blank(path, environ={'REQUEST_METHOD': 'PUT'},
                                headers={'X-Run-Storlet': 'Storlet-1.0.jar'},
                                body='FAKE APP')
            app = self.get_app(self.app, self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('201 Created', self.got_statuses[-1])
            put_calls = self.app.get_calls('PUT', target)
            self.assertEqual(len(put_calls), 1)
            self.assertEqual(put_calls[-1][3], 'FAKE APP')

        with storlet_enabled():
            put(target)

    def test_PUT_copy_without_storlets(self):
        target = '/v1/AUTH_a/c/to'
        copy_from = 'c/so'
        self.app.register('PUT', target, HTTPCreated)

        def copy():
            req = Request.blank(target, environ={'REQUEST_METHOD': 'PUT'},
                                headers={'X-Copy-From': copy_from,
                                         'X-Backend-Storage-Policy-Index': 0})
            app = self.get_app(self.app, self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('201 Created', self.got_statuses[-1])

        with authorize_storlet_execution() as ase:
            copy()
            self.assertEqual(0, ase.call_count)

    def test_PUT_copy_with_storlets(self):
        source = '/v1/AUTH_a/c/so'
        target = '/v1/AUTH_a/c/to'
        copy_from = 'c/so'
        self.app.register('GET', source, HTTPOk, body='source body')
        self.app.register('PUT', target, HTTPCreated)
        # TODO(eranr): should uncomment this after refactoring
        # storlet = '/v1/AUTH_a/storlets/Storlet-1.0.jar'
        # self.app.register('GET', storlet, HTTPOk, 'jar binary')

        def copy(target, source, copy_from):
            req = Request.blank(target, environ={'REQUEST_METHOD': 'PUT'},
                                headers={'X-Copy-From': copy_from,
                                         'X-Run-Storlet': 'Storlet-1.0.jar',
                                         'X-Backend-Storage-Policy-Index': 0})
            app = self.get_app(self.app, self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('201 Created', self.got_statuses[-1])
            get_calls = self.app.get_calls('GET', source)
            self.assertEqual(len(get_calls), 1)
            self.assertEqual(get_calls[-1][3], '')
            self.assertEqual(get_calls[-1][1], source)
            put_calls = self.app.get_calls('PUT', target)
            self.assertEqual(len(put_calls), 1)
            self.assertEqual(put_calls[-1][3], 'source body')
        with storlet_enabled():
            copy(target, source, copy_from)

    def test_COPY_verb_without_storlets(self):
        source = '/v1/AUTH_a/c/so'
        destination = 'c/to'
        self.app.register('COPY', source, HTTPCreated)

        def copy():
            req = Request.blank(source, environ={'REQUEST_METHOD': 'COPY'},
                                headers={'Destination': destination,
                                         'X-Backend-Storage-Policy-Index': 0})
            app = self.get_app(self.app, self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('201 Created', self.got_statuses[-1])

        with mock.patch(
                'storlet_gateway.storlet_stub_gateway.StorletGatewayStub.'
                'authorizeStorletExecution') as m:
            copy()
            self.assertEqual(0, m.call_count)

    def test_COPY_verb_with_storlets(self):
        source = '/v1/AUTH_a/c/so'
        target = '/v1/AUTH_a/c/to'
        destination = 'c/to'
        self.app.register('GET', source, HTTPOk, body='source body')
        self.app.register('PUT', target, HTTPCreated)
        # TODO(eranr): should uncomment this after refactoring
        # storlet = '/v1/AUTH_a/storlets/Storlet-1.0.jar'
        # self.app.register('GET', storlet, HTTPOk, 'jar binary')

        def copy(target, source, destination):
            req = Request.blank(source, environ={'REQUEST_METHOD': 'COPY'},
                                headers={'Destination': destination,
                                         'X-Run-Storlet': 'Storlet-1.0.jar',
                                         'X-Backend-Storage-Policy-Index': 0})
            app = self.get_app(self.app, self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('201 Created', self.got_statuses[-1])
            get_calls = self.app.get_calls('GET', source)
            self.assertEqual(len(get_calls), 1)
            self.assertEqual(get_calls[-1][3], '')
            self.assertEqual(get_calls[-1][1], source)
            put_calls = self.app.get_calls('PUT', target)
            self.assertEqual(len(put_calls), 1)
            self.assertEqual(put_calls[-1][3], 'source body')
        with storlet_enabled():
            copy(target, source, destination)

    def test_copy_with_unsupported_headers(self):
        target = '/v1/AUTH_a/c/o'

        def copy(method, copy_header):
            base_headers = {'X-Run-Storlet': 'Storlet-1.0.jar',
                            'X-Backend-Storage-Policy-Index': 0}
            base_headers.update(copy_header)
            req = Request.blank(target, environ={'REQUEST_METHOD': method},
                                headers=base_headers)
            app = self.get_app(self.app, self.conf)
            app(req.environ, self.start_response)

        with storlet_enabled():
            self.assertRaises(HTTPBadRequest,
                              copy('COPY', {'Destination-Account': 'a'}))
            self.assertRaises(HTTPBadRequest,
                              copy('COPY', {'x-fresh-metadata': ''}))
            self.assertRaises(HTTPBadRequest,
                              copy('PUT', {'X-Copy-From-Account': 'a'}))
            self.assertRaises(HTTPBadRequest,
                              copy('PUT', {'x-fresh-metadata': ''}))

    def test_PUT_storlet(self):
        target = '/v1/AUTH_a/storlet/storlet-1.0.jar'
        self.app.register('PUT', target, HTTPCreated)

        def put(path):
            sheaders = {'X-Object-Meta-Storlet-Language': 'Java',
                        'X-Object-Meta-Storlet-Interface-Version': '1.0',
                        'X-Object-Meta-Storlet-Dependency': 'dependency',
                        'X-Object-Meta-Storlet-Main':
                            'org.openstack.storlet.Storlet'}
            req = Request.blank(path, environ={'REQUEST_METHOD': 'PUT'},
                                headers=sheaders)
            app = self.get_app(self.app, self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('201 Created', self.got_statuses[-1])

        with storlet_enabled():
            put(target)

    def test_PUT_storlet_mandatory_parameter_fails(self):
        target = '/v1/AUTH_a/storlet/storlet-1.0.jar'
        self.app.register('PUT', target, HTTPCreated)

        drop_headers = [
            ('X-Object-Meta-Storlet-Language', 'Language'),
            ('X-Object-Meta-Storlet-Interface-Version', 'Interface-Version'),
            ('X-Object-Meta-Storlet-Dependency', 'Dependency'),
            ('X-Object-Meta-Storlet-Main', 'Main'),
        ]

        def put(path, header, assertion):
            sheaders = {'X-Object-Meta-Storlet-Language': 'Java',
                        'X-Object-Meta-Storlet-Interface-Version': '1.0',
                        'X-Object-Meta-Storlet-Dependency': 'dependency',
                        'X-Object-Meta-Storlet-Main':
                            'org.openstack.storlet.Storlet'}
            del sheaders[header]
            req = Request.blank(path, environ={'REQUEST_METHOD': 'PUT'},
                                headers=sheaders)
            app = self.get_app(self.app, self.conf)
            app(req.environ, self.start_response)
            # FIXME(kota_): Unfortunately, we can not test yet here because
            # the validation is not in stub gateway but in docker gateway so
            # need more refactor to parse the functionality to be easy testing
            # self.assertEqual('400 BadRequest', self.got_statuses[-1])

        for header, assertion in drop_headers:
            with storlet_enabled():
                put(target, header, assertion)

    def test_POST_storlet(self):
        target = '/v1/AUTH_a/storlet/storlet-1.0.jar'
        self.app.register('POST', target, HTTPAccepted)

        def post(path):
            sheaders = {'X-Object-Meta-Storlet-Language': 'Java',
                        'X-Object-Meta-Storlet-Interface-Version': '1.0',
                        'X-Object-Meta-Storlet-Dependency': 'dependency',
                        'X-Object-Meta-Storlet-Main':
                            'org.openstack.storlet.Storlet'}
            req = Request.blank(path, environ={'REQUEST_METHOD': 'POST'},
                                headers=sheaders)
            app = self.get_app(self.app, self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('202 Accepted', self.got_statuses[-1])

        with storlet_enabled():
            post(target)

    def test_GET_storlet(self):
        target = '/v1/AUTH_a/storlet/storlet-1.0.jar'
        sheaders = {'X-Object-Meta-Storlet-Language': 'Java',
                    'X-Object-Meta-Storlet-Interface-Version': '1.0',
                    'X-Object-Meta-Storlet-Dependency': 'dependency',
                    'X-Object-Meta-Storlet-Main':
                        'org.openstack.storlet.Storlet'}
        self.app.register('GET', target, HTTPOk, headers=sheaders,
                          body='jar binary')

        def get(path):
            req = Request.blank(path, environ={'REQUEST_METHOD': 'GET'})
            app = self.get_app(self.app, self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['jar binary'])
            resp_headers = dict(self.got_headers[-1])
            for key in sheaders:
                self.assertEqual(resp_headers[key], sheaders[key])

        with storlet_enabled():
            get(target)

    def test_PUT_dependency(self):
        target = '/v1/AUTH_a/dependency/dependency'
        self.app.register('PUT', target, HTTPCreated)

        def put(path):
            sheaders = {'X-Object-Meta-Storlet-Dependency-Version': '1',
                        'X-Object-Meta-Storlet-Dependency-Permissions': '0755'}
            req = Request.blank(path, environ={'REQUEST_METHOD': 'PUT'},
                                headers=sheaders)
            app = self.get_app(self.app, self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('201 Created', self.got_statuses[-1])

        with storlet_enabled():
            put(target)

    def test_POST_dependency(self):
        target = '/v1/AUTH_a/dependency/dependency'
        self.app.register('POST', target, HTTPAccepted)

        def post(path):
            sheaders = {'X-Object-Meta-Storlet-Dependency-Version': '1',
                        'X-Object-Meta-Storlet-Dependency-Permissions': '0755'}
            req = Request.blank(path, environ={'REQUEST_METHOD': 'POST'},
                                headers=sheaders)
            app = self.get_app(self.app, self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('202 Accepted', self.got_statuses[-1])

        with storlet_enabled():
            post(target)

    def test_GET_dependency(self):
        target = '/v1/AUTH_a/dependency/dependency'
        sheaders = {'X-Object-Meta-Storlet-Dependency-Version': '1',
                    'X-Object-Meta-Storlet-Dependency-Permissions': '0755'}
        self.app.register('GET', target, HTTPOk, headers=sheaders,
                          body='FAKE APP')

        def get(path):
            req = Request.blank(path, environ={'REQUEST_METHOD': 'GET'})
            app = self.get_app(self.app, self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['FAKE APP'])
            resp_headers = dict(self.got_headers[-1])
            for key in sheaders:
                self.assertEqual(resp_headers[key], sheaders[key])

        with storlet_enabled():
            get(target)


class TestStorletMiddlewareObject(TestStorletMiddleware):
    def setUp(self):
        super(TestStorletMiddlewareObject, self).setUp()
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
        target = '/sda1/p/AUTH_a/storlet/storlet-1.0.jar'
        self.app.register('PUT', target, HTTPCreated)

        def put(path):
            sheaders = {'X-Object-Meta-Storlet-Language': 'Java',
                        'X-Object-Meta-Storlet-Interface-Version': '1.0',
                        'X-Object-Meta-Storlet-Dependency': 'dependency',
                        'X-Object-Meta-Storlet-Main':
                            'org.openstack.storlet.Storlet'}
            req = Request.blank(path, environ={'REQUEST_METHOD': 'PUT'},
                                headers=sheaders)
            app = self.get_app(self.app, self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('201 Created', self.got_statuses[-1])

        put(target)

    def test_GET_without_storlets(self):
        def basic_get(path):
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'},
                headers={'X-Backend-Storlet-Policy-Index': '0'})
            self.app.register('GET', path, HTTPOk, body='FAKE APP')
            app = self.get_app(self.app, self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['FAKE APP'])
            self.app.reset_all()

        for target in ('/sda1/p/AUTH_a', '/sda1/p/AUTH_a/c',
                       '/sda1/p/AUTH_a/c/o'):
            basic_get(target)

    def test_GET_with_storlets(self):
        target = '/sda1/p/AUTH_a/c/o'
        self.app.register('GET', target, HTTPOk, body='FAKE APP')

        def get(path):
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'},
                headers={'X-Backend-Storlet-Policy-Index': '0',
                         'X-Run-Storlet': 'Storlet-1.0.jar'})
            app = self.get_app(self.app, self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp.read(), 'FAKE APP')

        get(target)

    def test_GET_with_storlets_and_http_range(self):
        target = '/sda1/p/AUTH_a/c/o'
        self.app.register('GET', target, HTTPOk, body='FAKE APP')

        def get(path):
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'},
                headers={'X-Backend-Storlet-Policy-Index': '0',
                         'X-Run-Storlet': 'Storlet-1.0.jar',
                         'Range': 'bytes=10-20'})
            app = self.get_app(self.app, self.conf)
            app(req.environ, self.start_response)
            self.assertEqual('416 Requested Range Not Satisfiable',
                             self.got_statuses[-1])

        get(target)

    def test_GET_with_storlets_and_storlet_range(self):
        target = '/sda1/p/AUTH_a/c/o'
        self.app.register('GET', target, HTTPOk, body='FAKE APP')

        def get(path):
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'},
                headers={'X-Backend-Storlet-Policy-Index': '0',
                         'X-Run-Storlet': 'Storlet-1.0.jar',
                         'X-Storlet-Range': 'bytes=1-6',
                         'Range': 'bytes=1-6'})
            app = self.get_app(self.app, self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('206 Partial Content',
                             self.got_statuses[-1])
            self.assertEqual(resp, ['AKE AP'])

        get(target)

    def test_GET_slo_manifest_with_storlets(self):
        target = '/sda1/p/AUTH_a/c/o'
        self.app.register('GET', target, HTTPOk,
                          headers={'X-Static-Large-Object': 'True'},
                          body='FAKE MANIFEST')

        def get(path):
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'},
                headers={'X-Backend-Storlet-Policy-Index': '0',
                         'X-Run-Storlet': 'Storlet-1.0.jar'})
            app = self.get_app(self.app, self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['FAKE MANIFEST'])

        get(target)

    def test_GET_slo_segment_with_storlets(self):
        target = '/sda1/p/AUTH_a/c/o'
        self.app.register('GET', target, HTTPOk,
                          headers={'X-Static-Large-Object': 'True'},
                          body='FAKE SEGMENT')

        def get(path):
            req = Request.blank(
                path, environ={'REQUEST_METHOD': 'GET'},
                headers={'X-Backend-Storlet-Policy-Index': '0',
                         'multipart-manifest': 'get',
                         'X-Run-Storlet': 'Storlet-1.0.jar'})
            app = self.get_app(self.app, self.conf)
            resp = app(req.environ, self.start_response)
            self.assertEqual('200 OK', self.got_statuses[-1])
            self.assertEqual(resp, ['FAKE SEGMENT'])

        get(target)


class TestStorletBaseHandler(unittest.TestCase):
    def test_init_failed_via_base_handler(self):
        def assert_not_implemented(method, path, headers):
            req = Request.blank(
                path, environ={'REQUEST_METHOD': method},
                headers=headers)
            try:
                BaseStorletHandler(
                    req, mock.MagicMock(), mock.MagicMock(), mock.MagicMock())
            except NotImplementedError:
                pass
            except Exception as e:
                self.fail('Unexpected Error: %s raised with %s, %s, %s' %
                          (repr(e), path, method, headers))

        for method in ('PUT', 'GET', 'POST'):
            for path in ('', '/v1', '/v1/a', '/v1/a/c', '/v1/a/c/o'):
                for headers in ({}, {'X-Run-Storlet': 'Storlet-1.0.jar'}):
                    assert_not_implemented(method, path, headers)


class TestStorletProxyHandler(unittest.TestCase):
    def setUp(self):
        self.handler_class = StorletProxyHandler

    def test_init_handler(self):
        req = Request.blank(
            '/v1/acc/cont/obj', environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar'})
        with storlet_enabled():
            handler = self.handler_class(
                req, mock.MagicMock(), mock.MagicMock(), mock.MagicMock())

        self.assertEqual('/v1/acc/cont/obj', handler.request.path)
        self.assertEqual('v1', handler.api_version)
        self.assertEqual('acc', handler.account)
        self.assertEqual('cont', handler.container)
        self.assertEqual('obj', handler.obj)

        # overwrite the request
        # TODO(kota_): is it good to raise an error immediately?
        #              or re-validate the req again?
        req = Request.blank(
            '/v2/acc2/cont2/obj2', environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar'})
        handler.request = req
        self.assertEqual('/v2/acc2/cont2/obj2', handler.request.path)
        self.assertEqual('v2', handler.api_version)
        self.assertEqual('acc2', handler.account)
        self.assertEqual('cont2', handler.container)
        self.assertEqual('obj2', handler.obj)

        # no direct assignment allowed
        with self.assertRaises(AttributeError):
            handler.api_version = '1'

        with self.assertRaises(AttributeError):
            handler.account = 'acc'

        with self.assertRaises(AttributeError):
            handler.container = 'cont'

        with self.assertRaises(AttributeError):
            handler.obj = 'obj'


class TestStorletObjectHandler(unittest.TestCase):
    def setUp(self):
        self.handler_class = StorletObjectHandler

    def test_init_handler(self):
        req = Request.blank(
            '/dev/part/acc/cont/obj', environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar'})
        handler = self.handler_class(
            req, mock.MagicMock(), mock.MagicMock(), mock.MagicMock())
        # FIXME: stil hold api version 0 at ObjectHandler but will be
        #        deprecated if it's never used.
        self.assertEqual('0', handler.api_version)
        self.assertEqual('acc', handler.account)
        self.assertEqual('cont', handler.container)
        self.assertEqual('obj', handler.obj)

        req = Request.blank(
            '/dev/part/acc2/cont2/obj2', environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar'})
        handler.request = req
        self.assertEqual('/dev/part/acc2/cont2/obj2', handler.request.path)
        self.assertEqual('0', handler.api_version)
        self.assertEqual('acc2', handler.account)
        self.assertEqual('cont2', handler.container)
        self.assertEqual('obj2', handler.obj)

        # no direct assignment allowed
        with self.assertRaises(AttributeError):
            handler.api_version = '1'

        with self.assertRaises(AttributeError):
            handler.account = 'acc'

        with self.assertRaises(AttributeError):
            handler.container = 'cont'

        with self.assertRaises(AttributeError):
            handler.obj = 'obj'


if __name__ == '__main__':
    unittest.main()
