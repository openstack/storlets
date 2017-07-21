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
from contextlib import contextmanager
from six import StringIO

from swift.common.swob import Request
from storlets.gateway.common.exceptions import FileManagementError
from storlets.swift_middleware.handlers import StorletBaseHandler
from storlets.swift_middleware.handlers.base import get_container_names, \
    SwiftFileManager
from tests.unit import FakeLogger


class TestUtils(unittest.TestCase):
    def setUp(self):
        pass

    def test_get_container_names(self):
        # Use default values
        self.assertEqual(
            {'storlet': 'storlet', 'dependency': 'dependency',
             'log': 'storletlog'},
            get_container_names({}))

        # Use explicit values
        self.assertEqual(
            {'storlet': 'conta', 'dependency': 'contb', 'log': 'contc'},
            get_container_names(
                {'storlet_container': 'conta',
                 'storlet_dependency': 'contb',
                 'storlet_logcontainer': 'contc'}))


class TestSwiftFileManager(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.manager = SwiftFileManager('a', 'storlet', 'dependency', 'log',
                                        'client.conf', self.logger)

    @contextmanager
    def _mock_internal_client(self, cls):
        with mock.patch('storlets.swift_middleware.handlers.base.'
                        'InternalClient',
                        cls):
            yield

    def test_get_storlet(self):
        name = 'Storlet-1.0.jar'

        class DummyClient(object):
            def __init__(self, *args, **kwargs):
                pass

            def get_object(self, account, container, obj, headers,
                           acceptable_statuses=None):
                return '200', {}, StringIO('test')

        with self._mock_internal_client(DummyClient):
            data_iter, perm = self.manager.get_storlet(name)
            self.assertEqual('test', next(data_iter))
            self.assertIsNone(perm)

        class DummyClient(object):
            def __init__(self, *args, **kwargs):
                pass

            def get_object(self, account, container, obj, headers,
                           acceptable_statuses=None):
                raise Exception('Some error')

        with self._mock_internal_client(DummyClient):
            with self.assertRaises(FileManagementError):
                self.manager.get_storlet(name)

    def test_get_dependency(self):
        name = 'depfile'

        class DummyClient(object):
            def __init__(self, *args, **kwargs):
                pass

            def get_object(self, account, container, obj, headers,
                           acceptable_statuses=None):
                headers = {'X-Object-Meta-Storlet-Dependency-Permissions':
                           '0600'}
                return '200', headers, StringIO('test')

        with self._mock_internal_client(DummyClient):
            data_iter, perm = self.manager.get_dependency(name)
            self.assertEqual('test', next(data_iter))
            self.assertEqual('0600', perm)

        class DummyClient(object):
            def __init__(self, *args, **kwargs):
                pass

            def get_object(self, account, container, obj, headers,
                           acceptable_statuses=None):
                return '200', {}, StringIO('test')

        with self._mock_internal_client(DummyClient):
            data_iter, perm = self.manager.get_dependency(name)
            self.assertEqual('test', next(data_iter))
            self.assertIsNone(perm)

        class DummyClient(object):
            def __init__(self, *args, **kwargs):
                pass

            def get_object(self, account, container, obj, headers,
                           acceptable_statuses=None):
                raise Exception('Some error')

        with self._mock_internal_client(DummyClient):
            with self.assertRaises(FileManagementError):
                self.manager.get_dependency(name)

    def test_put_log(self):
        name = 'logfile'

        class DummyClient(object):
            def __init__(self, *args, **kwargs):
                pass

            def upload_object(self, fobj, account, container, obj,
                              headers=None):
                pass

        with self._mock_internal_client(DummyClient):
            self.manager.put_log(name, mock.MagicMock())

        class DummyClient(object):
            def __init__(self, *args, **kwargs):
                pass

            def upload_object(self, fobj, account, container, obj,
                              headers=None):
                raise Exception('Some error')

        with self._mock_internal_client(DummyClient):
            with self.assertRaises(FileManagementError):
                self.manager.put_log(name, mock.MagicMock())


class TestStorletBaseHandler(unittest.TestCase):

    def test_init_failed_via_base_handler(self):
        def assert_not_implemented(method, path, headers):
            req = Request.blank(
                path, environ={'REQUEST_METHOD': method},
                headers=headers)
            with self.assertRaises(NotImplementedError):
                StorletBaseHandler(
                    req, mock.MagicMock(), mock.MagicMock(),
                    mock.MagicMock(), mock.MagicMock())

        for method in ('PUT', 'GET', 'POST'):
            for path in ('', '/v1', '/v1/a', '/v1/a/c', '/v1/a/c/o'):
                for headers in ({}, {'X-Run-Storlet': 'Storlet-1.0.jar'}):
                    assert_not_implemented(method, path, headers)

    def test_parameters_from_headers(self):
        def mock_request_property():
            """
            This is for skipping extract_vaco which causes NotImplementedError
            if initialize StorletBaseHandler directly.
            """
            def getter(self):
                return self._request

            def setter(self, request):
                self._request = request

            return property(getter, setter, doc='mocked prop')

        headers = {'X-Storlet-Parameter-1': '1:2:3:4',
                   'X-Storlet-parameter-Z': 'A:c'}
        req = Request.blank(
            '/v1/a/c/o', environ={'REQUEST_METHOD': 'GET'},
            headers=headers)

        with mock.patch('storlets.swift_middleware.handlers.base.'
                        'StorletBaseHandler.request', mock_request_property):
            handler = StorletBaseHandler(
                req, mock.MagicMock(), mock.MagicMock(),
                mock.MagicMock(), mock.MagicMock())
            handler._update_storlet_parameters_from_headers()
            self.assertEqual('2:3:4', handler.request.params['1'])
            self.assertEqual('c', handler.request.params['A'])


if __name__ == '__main__':
    unittest.main()
