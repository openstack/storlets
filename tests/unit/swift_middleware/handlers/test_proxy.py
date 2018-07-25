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

import mock
import unittest
import itertools

from contextlib import contextmanager
from swift.common.swob import Request, HTTPOk, HTTPCreated, HTTPAccepted, \
    HTTPNoContent, HTTPNotFound
from storlets.swift_middleware.handlers import StorletProxyHandler
from storlets.swift_middleware.handlers.proxy import REFERER_PREFIX

from tests.unit.swift_middleware.handlers import \
    BaseTestStorletMiddleware, create_handler_config


@contextmanager
def fake_acc_info(acc_info):
    with mock.patch('storlets.swift_middleware.handlers.proxy.'
                    'get_account_info') as ai:
        ai.return_value = acc_info
        yield


@contextmanager
def storlet_enabled():
    acc_info = {'meta': {'storlet-enabled': 'true'}}
    with fake_acc_info(acc_info):
        yield


class TestStorletMiddlewareProxy(BaseTestStorletMiddleware):
    def setUp(self):
        super(TestStorletMiddlewareProxy, self).setUp(exec_server='proxy')

    def test_load_app(self):
        try:
            self.get_app(self.base_app, self.conf)
        except Exception:
            self.fail('Application loading got an error')

    def get_request_response(self, target, method, headers=None, body=None):
        # Ensure the body is byte format on py3, this is needed until
        # swift's Request supports byte format body when body is None in args
        body = body or b''
        req = Request.blank(target, environ={'REQUEST_METHOD': method},
                            headers=headers, body=body)
        return self.get_response(req)

    def test_GET_without_storlets(self):
        def basic_get(path):
            self.base_app.register('GET', path, HTTPOk, body=b'FAKE APP')
            resp = self.get_request_response(path, 'GET')
            self.assertEqual('200 OK', resp.status)
            self.assertEqual(b'FAKE APP', resp.body)
            self.base_app.reset_all()

        for target in ('AUTH_a', 'AUTH_a/c', 'AUTH_a/c/o'):
            path = '/'.join(['', 'v1', target])
            basic_get(path)

    def test_GET_with_storlets(self):
        # TODO(takashi): decide request path based on config value
        target = '/v1/AUTH_a/c/o'
        self.base_app.register('GET', target, HTTPOk, body=b'FAKE RESULT')
        storlet = '/v1/AUTH_a/storlet/Storlet-1.0.jar'
        self.base_app.register('GET', storlet, HTTPOk, headers={},
                               body=b'jar binary')

        acc_info = {'meta': {'storlet-enabled': 'true'}}
        with fake_acc_info(acc_info):
            headers = {'X-Run-Storlet': 'Storlet-1.0.jar'}
            resp = self.get_request_response(target, 'GET', headers=headers)
            self.assertEqual('200 OK', resp.status)
            self.assertEqual(b'FAKE RESULT', resp.body)
            calls = self.base_app.get_calls()

            # Make sure now we sent two requests to swift
            self.assertEqual(2, len(calls))

            # The first one is HEAD request to storlet object
            self.assertEqual('HEAD', calls[0][0])
            self.assertEqual(storlet, calls[0][1])

            # The last one is exexution GET call
            self.assertEqual(target, calls[-1][1])
            self.assertIn('X-Run-Storlet', calls[-1][2])

    def test_GET_with_storlets_disabled_account(self):
        target = '/v1/AUTH_a/c/o'

        acc_info = {'meta': {}}
        with fake_acc_info(acc_info):
            headers = {'X-Run-Storlet': 'Storlet-1.0.jar'}
            resp = self.get_request_response(target, 'GET', headers=headers)
            self.assertEqual('400 Bad Request', resp.status)

            calls = self.base_app.get_calls()
            self.assertEqual(0, len(calls))

    def test_GET_with_storlets_object_404(self):
        target = '/v1/AUTH_a/c/o'
        self.base_app.register('GET', target, HTTPNotFound)
        storlet = '/v1/AUTH_a/storlet/Storlet-1.0.jar'
        self.base_app.register('GET', storlet, HTTPOk, body=b'jar binary')

        with storlet_enabled():
            headers = {'X-Run-Storlet': 'Storlet-1.0.jar'}
            resp = self.get_request_response(target, 'GET', headers=headers)
            self.assertEqual('404 Not Found', resp.status)

            calls = self.base_app.get_calls()
            self.assertEqual(2, len(calls))

    def test_GET_with_storlets_and_http_range(self):
        target = '/v1/AUTH_a/c/o'

        with storlet_enabled():
            headers = {'X-Run-Storlet': 'Storlet-1.0.jar',
                       'Range': 'bytes=10-20'}
            resp = self.get_request_response(target, 'GET', headers=headers)
            self.assertEqual('400 Bad Request', resp.status)

    def test_GET_with_storlets_and_storlet_range(self):
        target = '/v1/AUTH_a/c/o'
        self.base_app.register('GET', target, HTTPOk, body=b'FAKE APP')
        storlet = '/v1/AUTH_a/storlet/Storlet-1.0.jar'
        self.base_app.register('GET', storlet, HTTPOk, body=b'jar binary')

        with storlet_enabled():
            req_range = 'bytes=1-6'
            headers = {'X-Run-Storlet': 'Storlet-1.0.jar',
                       'X-Storlet-Run-On-Proxy': '',
                       'X-Storlet-Range': req_range}
            resp = self.get_request_response(target, 'GET', headers=headers)
            self.assertEqual('200 OK', resp.status)
            self.assertEqual(b'AKE AP', resp.body)

            self.assertNotIn('Content-Range', resp.headers)
            self.assertEqual('bytes 1-6/8',
                             resp.headers['Storlet-Input-Range'])

            raw_req = self.base_app.get_calls('GET', target)[0]
            for key in ['Range', 'X-Storlet-Range']:
                self.assertEqual(raw_req[2][key], req_range)

    def test_GET_with_storlets_and_object_storlet_range(self):
        # Create a single range request that needs to be
        # processed by the object handler
        target = '/v1/AUTH_a/c/o'
        self.base_app.register('GET', target, HTTPOk, body=b'FAKE APP')
        storlet = '/v1/AUTH_a/storlet/Storlet-1.0.jar'
        self.base_app.register('GET', storlet, HTTPOk, body=b'jar binary')

        with storlet_enabled():
            req_range = 'bytes=1-6'
            headers = {'X-Run-Storlet': 'Storlet-1.0.jar',
                       'X-Storlet-Range': req_range}
            resp = self.get_request_response(target, 'GET', headers=headers)
            # We assert that nothing actually happens
            # by the proxy handler
            self.assertEqual('200 OK', resp.status)
            self.assertEqual(b'FAKE APP', resp.body)

    def test_GET_with_storlets_and_extra_resourece(self):
        target = '/v1/AUTH_a/c/o'
        self.base_app.register('GET', target, HTTPOk, body=b'FAKE APP')
        extra_target = '/v1/AUTH_a/c2/o2'
        self.base_app.register('GET', extra_target, HTTPOk, body=b'Whooa')
        storlet = '/v1/AUTH_a/storlet/Storlet-1.0.jar'
        self.base_app.register('GET', storlet, HTTPOk, body=b'jar binary')

        with storlet_enabled():
            headers = {'X-Run-Storlet': 'Storlet-1.0.jar',
                       'X-Storlet-Extra-Resources': '/c2/o2'}
            resp = self.get_request_response(target, 'GET', headers=headers)
            self.assertEqual('200 OK', resp.status)
            self.assertEqual(b'FAKE APP', resp.body)

            # GET target called
            self.assertTrue(any(self.base_app.get_calls('GET', target)))
            # GET extra target also called
            self.assertTrue(any(self.base_app.get_calls('GET', extra_target)))

    def test_GET_slo_without_storlets(self):
        target = '/v1/AUTH_a/c/slo_manifest'
        self.base_app.register('GET', target, HTTPOk,
                               headers={'x-static-large-object': 'True'},
                               body=b'FAKE APP')
        resp = self.get_request_response(target, 'GET')
        self.assertEqual(b'FAKE APP', resp.body)

    def test_GET_slo_with_storlets(self):
        target = '/v1/AUTH_a/c/slo_manifest'
        self.base_app.register('GET', target, HTTPOk,
                               headers={'x-static-large-object': 'True'},
                               body=b'FAKE APP')
        storlet = '/v1/AUTH_a/storlet/Storlet-1.0.jar'
        self.base_app.register('GET', storlet, HTTPOk, body=b'jar binary')

        with storlet_enabled():
            headers = {'X-Run-Storlet': 'Storlet-1.0.jar'}
            resp = self.get_request_response(target, 'GET', headers=headers)
            self.assertEqual('200 OK', resp.status)
            self.assertEqual(b'FAKE APP', resp.body)

            calls = self.base_app.get_calls()
            self.assertEqual(2, len(calls))

    def test_GET_with_storlets_no_object(self):
        target = '/v1/AUTH_a/c/'
        self.base_app.register('GET', target, HTTPOk,
                               body=b'FAKE APP')
        with storlet_enabled():
            headers = {'X-Run-Storlet': 'Storlet-1.0.jar'}
            resp = self.get_request_response(target, 'GET', headers=headers)
            self.assertEqual('200 OK', resp.status)
            self.assertEqual(b'FAKE APP', resp.body)

            # Make sure now we sent one request to swift
            # that is, storlets path was not executed
            # due to no object in target
            calls = self.base_app.get_calls()
            self.assertEqual(1, len(calls))

    def test_PUT_without_storlets(self):
        def basic_put(path):
            self.base_app.register('PUT', path, HTTPCreated)
            resp = self.get_request_response(path, 'PUT')
            self.assertEqual('201 Created', resp.status)
            self.base_app.reset_all()

        for target in ('AUTH_a', 'AUTH_a/c', 'AUTH_a/c/o'):
            path = '/'.join(['', 'v1', target])
            basic_put(path)

    def test_PUT_with_storlets(self):
        target = '/v1/AUTH_a/c/o'
        self.base_app.register('PUT', target, HTTPCreated, body=b'')
        storlet = '/v1/AUTH_a/storlet/Storlet-1.0.jar'
        self.base_app.register('GET', storlet, HTTPOk, body=b'jar binary')

        with storlet_enabled():
            headers = {'X-Run-Storlet': 'Storlet-1.0.jar'}
            resp = self.get_request_response(target, 'PUT', headers=headers,
                                             body=b'FAKE APP')
            self.assertEqual('201 Created', resp.status)

            calls = self.base_app.get_calls()
            # Make sure now we sent two requests to swift
            self.assertEqual(2, len(calls))

            # The first one is HEAD request to storlet object
            self.assertEqual('HEAD', calls[0][0])
            self.assertEqual(storlet, calls[0][1])

            # The last one is PUT request about processed object
            self.assertEqual('PUT', calls[-1][0])
            self.assertEqual(target, calls[-1][1])
            self.assertEqual(b'FAKE APP', calls[-1][3])

    def test_PUT_with_storlets_no_object(self):
        target = '/v1/AUTH_a/c/'
        self.base_app.register('PUT', target, HTTPCreated)
        with storlet_enabled():
            headers = {'X-Run-Storlet': 'Storlet-1.0.jar'}
            resp = self.get_request_response(target, 'PUT', headers=headers,
                                             body=b'FAKE APP')
            self.assertEqual('201 Created', resp.status)

            calls = self.base_app.get_calls()
            # Make sure now we sent one request to swift
            # that is, storlets path was not executed
            # due to no object in target
            self.assertEqual(1, len(calls))

    def test_PUT_copy_without_storlets(self):
        target = '/v1/AUTH_a/c/to'
        copy_from = 'c/so'
        self.base_app.register('PUT', target, HTTPCreated)

        headers = {'X-Copy-From': copy_from,
                   'X-Backend-Storage-Policy-Index': 0}
        resp = self.get_request_response(target, 'PUT', headers=headers)
        self.assertEqual('201 Created', resp.status)

    def test_PUT_copy_with_storlets(self):
        source = '/v1/AUTH_a/c/so'
        target = '/v1/AUTH_a/c/to'
        copy_from = 'c/so'
        self.base_app.register('GET', source, HTTPOk,
                               headers={'x-object-meta-name': 'name'},
                               body=b'source body')
        self.base_app.register('PUT', target, HTTPCreated)
        storlet = '/v1/AUTH_a/storlet/Storlet-1.0.jar'
        self.base_app.register('GET', storlet, HTTPOk, body=b'jar binary')

        with storlet_enabled():
            headers = {'X-Copy-From': copy_from,
                       'X-Run-Storlet': 'Storlet-1.0.jar',
                       'X-Backend-Storage-Policy-Index': 0}
            resp = self.get_request_response(target, 'PUT', headers=headers)
            self.assertEqual('201 Created', resp.status)
            get_calls = self.base_app.get_calls('GET', source)
            self.assertEqual(1, len(get_calls))
            self.assertEqual(b'', get_calls[-1][3])
            self.assertEqual(source, get_calls[-1][1])
            self.assertIn('X-Run-Storlet', get_calls[-1][2])
            put_calls = self.base_app.get_calls('PUT', target)
            self.assertEqual(1, len(put_calls))
            self.assertEqual(b'source body', put_calls[-1][3])
            self.assertIn('X-Object-Meta-Name', dict(put_calls[-1][2]))
            self.assertEqual('name', put_calls[-1][2]['X-Object-Meta-Name'])
            self.assertNotIn('X-Run-Storlet', put_calls[-1][2])
            # no invocation (at gateway stub) at proxy
            for debug_line in self.logger.get_log_lines('debug'):
                self.assertNotIn("Identity invocation is called", debug_line)

    def test_PUT_copy_with_storlets_run_on_proxy(self):
        source = '/v1/AUTH_a/c/so'
        target = '/v1/AUTH_a/c/to'
        copy_from = 'c/so'
        self.base_app.register('GET', source, HTTPOk,
                               headers={'x-object-meta-name': 'name'},
                               body=b'source body')
        self.base_app.register('PUT', target, HTTPCreated)
        storlet = '/v1/AUTH_a/storlet/Storlet-1.0.jar'
        self.base_app.register('GET', storlet, HTTPOk, body=b'jar binary')

        with storlet_enabled():
            headers = {'X-Copy-From': copy_from,
                       'X-Run-Storlet': 'Storlet-1.0.jar',
                       'X-Storlet-Run-On-Proxy': '',
                       'X-Backend-Storage-Policy-Index': 0}
            resp = self.get_request_response(target, 'PUT', headers=headers)
            self.assertEqual('201 Created', resp.status)
            get_calls = self.base_app.get_calls('GET', source)
            self.assertEqual(1, len(get_calls))
            self.assertEqual(b'', get_calls[-1][3])
            self.assertEqual(source, get_calls[-1][1])
            self.assertNotIn('X-Run-Storlet', get_calls[-1][2])
            put_calls = self.base_app.get_calls('PUT', target)
            self.assertEqual(1, len(put_calls))
            self.assertEqual(b'source body', put_calls[-1][3])
            self.assertIn('X-Object-Meta-Name', dict(put_calls[-1][2]))
            self.assertEqual('name', put_calls[-1][2]['X-Object-Meta-Name'])
            self.assertNotIn('X-Run-Storlet', put_calls[-1][2])
            # no invocation at proxy
            for debug_line in self.logger.get_log_lines('debug'):
                if "Identity invocation is called" in debug_line:
                    break
            else:
                self.fail('no invocation message found at proxy')

    def test_COPY_verb_without_storlets(self):
        source = '/v1/AUTH_a/c/so'
        destination = 'c/to'
        self.base_app.register('COPY', source, HTTPCreated)

        headers = {'Destination': destination,
                   'X-Backend-Storage-Policy-Index': 0}
        resp = self.get_request_response(source, 'COPY', headers=headers)
        self.assertEqual('201 Created', resp.status)

    def test_COPY_verb_with_storlets(self):
        source = '/v1/AUTH_a/c/so'
        target = '/v1/AUTH_a/c/to'
        destination = 'c/to'
        self.base_app.register('GET', source, HTTPOk,
                               headers={'x-object-meta-name': 'name'},
                               body=b'source body')
        self.base_app.register('PUT', target, HTTPCreated)
        storlet = '/v1/AUTH_a/storlet/Storlet-1.0.jar'
        self.base_app.register('GET', storlet, HTTPOk, body=b'jar binary')

        with storlet_enabled():
            headers = {'Destination': destination,
                       'X-Run-Storlet': 'Storlet-1.0.jar',
                       'X-Backend-Storage-Policy-Index': 0}
            resp = self.get_request_response(source, 'COPY', headers=headers)
            self.assertEqual('201 Created', resp.status)
            get_calls = self.base_app.get_calls('GET', source)
            self.assertEqual(1, len(get_calls))
            self.assertEqual(b'', get_calls[-1][3])
            self.assertEqual(source, get_calls[-1][1])
            self.assertIn('X-Run-Storlet', get_calls[-1][2])
            put_calls = self.base_app.get_calls('PUT', target)
            self.assertEqual(1, len(put_calls))
            self.assertEqual(b'source body', put_calls[-1][3])
            self.assertEqual('name', put_calls[-1][2]['X-Object-Meta-Name'])
            self.assertNotIn('X-Run-Storlet', put_calls[-1][2])
            # no invocation at proxy
            for debug_line in self.logger.get_log_lines('debug'):
                self.assertNotIn("Identity invocation is called", debug_line)

    def test_COPY_verb_with_storlets_run_on_porxy(self):
        source = '/v1/AUTH_a/c/so'
        target = '/v1/AUTH_a/c/to'
        destination = 'c/to'
        self.base_app.register('GET', source, HTTPOk,
                               headers={'x-object-meta-name': 'name'},
                               body=b'source body')
        self.base_app.register('PUT', target, HTTPCreated)
        storlet = '/v1/AUTH_a/storlet/Storlet-1.0.jar'
        self.base_app.register('GET', storlet, HTTPOk, body=b'jar binary')

        with storlet_enabled():
            headers = {'Destination': destination,
                       'X-Run-Storlet': 'Storlet-1.0.jar',
                       'X-Storlet-Run-On-Proxy': '',
                       'X-Backend-Storage-Policy-Index': 0}
            resp = self.get_request_response(source, 'COPY', headers=headers)
            self.assertEqual('201 Created', resp.status)
            get_calls = self.base_app.get_calls('GET', source)
            self.assertEqual(1, len(get_calls))
            self.assertEqual(b'', get_calls[-1][3])
            self.assertEqual(source, get_calls[-1][1])
            self.assertNotIn('X-Run-Storlet', get_calls[-1][2])
            put_calls = self.base_app.get_calls('PUT', target)
            self.assertEqual(1, len(put_calls))
            self.assertEqual(b'source body', put_calls[-1][3])
            self.assertEqual('name', put_calls[-1][2]['X-Object-Meta-Name'])
            self.assertNotIn('X-Run-Storlet', put_calls[-1][2])
            # no invocation at proxy
            for debug_line in self.logger.get_log_lines('debug'):
                if "Identity invocation is called" in debug_line:
                    break
            else:
                self.fail('no invocation message found at proxy')

    def test_copy_with_unsupported_headers(self):
        target = '/v1/AUTH_a/c/o'
        storlet = '/v1/AUTH_a/storlet/Storlet-1.0.jar'
        self.base_app.register('GET', storlet, HTTPOk, body=b'jar binary')

        def copy_400(method, copy_header):
            base_headers = {'X-Run-Storlet': 'Storlet-1.0.jar',
                            'X-Backend-Storage-Policy-Index': 0}
            base_headers.update(copy_header)
            resp = self.get_request_response(target, method,
                                             headers=base_headers)
            self.assertEqual('400 Bad Request', resp.status)

        cases = [('COPY', {'Destination-Account': 'a', 'Destination': 'c/o'}),
                 ('COPY', {'X-Fresh-Metadata': '', 'Destination': 'c/o'}),
                 ('PUT', {'X-Copy-From-Account': 'a', 'X-Copy-From': 'c/o'}),
                 ('PUT', {'X-Fresh-Metadata': '', 'X-Copy-From': 'c/o'})]

        for case in cases:
            with storlet_enabled():
                copy_400(case[0], case[1])

    def test_PUT_storlet(self):
        target = '/v1/AUTH_a/storlet/storlet-1.0.jar'
        self.base_app.register('PUT', target, HTTPCreated)

        with storlet_enabled():
            sheaders = {'X-Object-Meta-Storlet-Language': 'Java',
                        'X-Object-Meta-Storlet-Interface-Version': '1.0',
                        'X-Object-Meta-Storlet-Dependency': 'dependency',
                        'X-Object-Meta-Storlet-Main':
                            'org.openstack.storlet.Storlet'}
            resp = self.get_request_response(target, 'PUT', headers=sheaders)
            self.assertEqual('201 Created', resp.status)

    def test_PUT_storlet_mandatory_parameter_fails(self):
        target = '/v1/AUTH_a/storlet/storlet-1.0.jar'
        self.base_app.register('PUT', target, HTTPCreated)

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
            resp = self.get_request_response(path, 'PUT', headers=sheaders)
            # FIXME(kota_): Unfortunately, we can not test yet here because
            # the validation is not in stub gateway but in docker gateway so
            # need more refactor to parse the functionality to be easy testing
            # self.assertEqual('400 BadRequest', resp.status)
            self.assertEqual('201 Created', resp.status)

        for header, assertion in drop_headers:
            with storlet_enabled():
                put(target, header, assertion)

    def test_POST_storlet(self):
        target = '/v1/AUTH_a/storlet/storlet-1.0.jar'
        self.base_app.register('POST', target, HTTPAccepted)

        with storlet_enabled():
            sheaders = {'X-Object-Meta-Storlet-Language': 'Java',
                        'X-Object-Meta-Storlet-Interface-Version': '1.0',
                        'X-Object-Meta-Storlet-Dependency': 'dependency',
                        'X-Object-Meta-Storlet-Main':
                            'org.openstack.storlet.Storlet'}
            resp = self.get_request_response(target, 'POST', headers=sheaders)
            self.assertEqual('202 Accepted', resp.status)

    def test_GET_storlet(self):
        target = '/v1/AUTH_a/storlet/storlet-1.0.jar'
        sheaders = {'X-Object-Meta-Storlet-Language': 'Java',
                    'X-Object-Meta-Storlet-Interface-Version': '1.0',
                    'X-Object-Meta-Storlet-Dependency': 'dependency',
                    'X-Object-Meta-Storlet-Main':
                        'org.openstack.storlet.Storlet'}
        self.base_app.register('GET', target, HTTPOk, headers=sheaders,
                               body=b'jar binary')

        with storlet_enabled():
            resp = self.get_request_response(target, 'GET')
            self.assertEqual('200 OK', resp.status)
            self.assertEqual(b'jar binary', resp.body)
            for key in sheaders:
                self.assertEqual(sheaders[key], resp.headers.get(key))

    def test_PUT_dependency(self):
        target = '/v1/AUTH_a/dependency/dependency'
        self.base_app.register('PUT', target, HTTPCreated)

        with storlet_enabled():
            sheaders = {'X-Object-Meta-Storlet-Dependency-Version': '1',
                        'X-Object-Meta-Storlet-Dependency-Permissions': '0755'}
            resp = self.get_request_response(target, 'PUT', headers=sheaders)
            self.assertEqual('201 Created', resp.status)

    def test_POST_dependency(self):
        target = '/v1/AUTH_a/dependency/dependency'
        self.base_app.register('POST', target, HTTPAccepted)

        with storlet_enabled():
            sheaders = {'X-Object-Meta-Storlet-Dependency-Version': '1',
                        'X-Object-Meta-Storlet-Dependency-Permissions': '0755'}
            resp = self.get_request_response(target, 'POST', headers=sheaders)
            self.assertEqual('202 Accepted', resp.status)

    def test_GET_dependency(self):
        target = '/v1/AUTH_a/dependency/dependency'
        sheaders = {'X-Object-Meta-Storlet-Dependency-Version': '1',
                    'X-Object-Meta-Storlet-Dependency-Permissions': '0755'}
        self.base_app.register('GET', target, HTTPOk, headers=sheaders,
                               body=b'FAKE APP')

        with storlet_enabled():
            resp = self.get_request_response(target, 'GET')
            self.assertEqual('200 OK', resp.status)
            self.assertEqual(b'FAKE APP', resp.body)
            for key in sheaders:
                self.assertEqual(sheaders[key], resp.headers.get(key))

    def test_storlets_with_invalid_method(self):
        with storlet_enabled():
            headers = {'X-Run-Storlet': 'Storlet-1.0.jar'}
            resp = self.get_request_response('/v1/AUTH_a/c/o',
                                             '_parse_vaco',
                                             headers=headers)
            self.assertEqual('405 Method Not Allowed', resp.status)

    def test_POST_storlet_acl_bad_request(self):
        # Test wrong target elements
        headers = {'X-Storlet-Container-Read': 'aa',
                   'X-Storlet-Name': 'bb'}
        target = '/v1/AUTH_a/c/o'
        self.base_app.register('POST', target, HTTPNoContent, body=b'')
        with storlet_enabled():
            resp = self.get_request_response(target, 'POST', headers=headers)
            self.assertEqual('204 No Content', resp.status)

        # Test wrong target containers
        targets = ['/v1/AUTH_a/dependency/', '/v1/AUTH_a/storlet/']
        with storlet_enabled():
            for target in targets:
                resp = self.get_request_response(target, 'POST',
                                                 headers=headers)
                self.assertEqual('400 Bad Request', resp.status)
                msg = b'storlet ACL update cannot be a storlet container'
                self.assertEqual(msg, resp.body)

        # Test wrong headers content
        hlist = [{'X-Storlet-Container-Read': ''},
                 {'X-Storlet-Container-Read': 'a'},
                 {'X-Storlet-Container-Read': 'a',
                  'X-Storlet-Name': ''}]
        target = '/v1/AUTH_a/c/'
        with storlet_enabled():
            for headers in hlist:
                resp = self.get_request_response(target, 'POST',
                                                 headers=headers)
                self.assertEqual('400 Bad Request', resp.status)
                self.assertIn(b'missing a mandatory header', resp.body)

        # Test wrong ACL content
        hlist = [{'X-Storlet-Container-Read': 'a,b',
                  'X-Storlet-Name': 'c'},
                 {'X-Storlet-Container-Read': 'a',
                  'X-Storlet-Name': 'b,c'}]
        target = '/v1/AUTH_a/c/'
        with storlet_enabled():
            for headers in hlist:
                resp = self.get_request_response(target, 'POST',
                                                 headers=headers)
                self.assertEqual('400 Bad Request', resp.status)
                self.assertIn(b'mulformed storlet or user name', resp.body)

    def test_POST_storlet_acl(self):
        target = '/v1/AUTH_a/c'
        head_headers = {'x-container-read': 'adam'}
        self.base_app.register('HEAD', target, HTTPNoContent, head_headers)
        self.base_app.register('POST', target, HTTPNoContent)

        headers = {'X-Storlet-Container-Read': 'a',
                   'X-Storlet-Name': 'b'}
        expected_read_acl = 'adam,.r:storlets.a_b'
        with storlet_enabled():
            resp = self.get_request_response(target, 'POST', headers=headers)
            self.assertEqual('204 No Content', resp.status)
            head_calls = self.base_app.get_calls('HEAD', target)
            self.assertEqual(1, len(head_calls))
            post_calls = self.base_app.get_calls('POST', target)
            self.assertEqual(1, len(post_calls))
            self.assertEqual(expected_read_acl,
                             post_calls[-1][2]['X-Container-Read'])

    def test_GET_with_invalid_referrer(self):
        headers = [{'Referer': REFERER_PREFIX},
                   {'Referer': 'a.b.%s' % REFERER_PREFIX},
                   {'Referer': 'a.b.%s.c.d' % REFERER_PREFIX},
                   {'Referer': '//%s' % REFERER_PREFIX},
                   {'Referer': '%s.c.d' % REFERER_PREFIX}]
        targets = ['/v1/AUTH_a/c', '/v1/AUTH_a/c/o']
        ops = ['GET', 'HEAD']
        for target, op, header in itertools.product(targets, ops, headers):
            resp = self.get_request_response(target, op, headers=header)
            self.assertEqual('403 Forbidden', resp.status)


class TestStorletProxyHandler(unittest.TestCase):
    def setUp(self):
        self.handler_class = StorletProxyHandler
        self.conf = create_handler_config('proxy')
        self.gateway_conf = {}

    def test_init_handler(self):
        req = Request.blank(
            '/v1/acc/cont/obj', environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar'})
        with storlet_enabled():
            handler = self.handler_class(
                req, self.conf, self.gateway_conf,
                mock.MagicMock(), mock.MagicMock())

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

    def test_remove_storlet_headers(self):
        req = Request.blank(
            '/v1/acc/cont/obj', environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Backend-Storlet-Policy-Index': '0',
                     'X-Run-Storlet': 'Storlet-1.0.jar'})
        with storlet_enabled():
            handler = self.handler_class(
                req, self.conf, self.gateway_conf,
                mock.MagicMock(), mock.MagicMock())

        headers = {'X-Storlet-Key1': 'Value1',
                   'X-Key2': 'Value2',
                   'X-Object-Meta-Storlet-Key3': 'Value3',
                   'X-Object-Meta-Key4': 'Value4'}
        handler._remove_storlet_headers(headers)

        self.assertNotIn('X-Storlet-Key1', headers)
        self.assertEqual('Value2', headers['X-Key2'])
        self.assertNotIn('X-Object-Meta-Storlet-Key3', headers)
        self.assertEqual('Value4', headers['X-Object-Meta-Key4'])

    def test_get_storlet_invocation_options(self):
        req = Request.blank(
            '/v1/acc/cont/obj',
            environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Run-Storlet': 'Storlet-1.0.jar',
                     'X-Storlet-Foo': 'baa'})
        with storlet_enabled():
            handler = self.handler_class(
                req, self.conf, self.gateway_conf, mock.MagicMock(),
                mock.MagicMock())

        options = handler._get_storlet_invocation_options(req)
        self.assertEqual('baa', options['storlet_foo'])
        self.assertFalse(options['generate_log'])

        req = Request.blank(
            '/v1/acc/cont/obj',
            environ={'REQUEST_METHOD': 'GET'},
            headers={'X-Run-Storlet': 'Storlet-1.0.jar',
                     'X-Storlet-Foo': 'baa',
                     'X-Storlet-Generate-Log': 'True'})
        with storlet_enabled():
            handler = self.handler_class(
                req, self.conf, self.gateway_conf, mock.MagicMock(),
                mock.MagicMock())

        options = handler._get_storlet_invocation_options(req)
        self.assertEqual('baa', options['storlet_foo'])
        self.assertTrue(options['generate_log'])


if __name__ == '__main__':
    unittest.main()
