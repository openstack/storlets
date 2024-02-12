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

import eventlet
from io import BytesIO, StringIO
import json
from shutil import rmtree
from tempfile import mkdtemp
import unittest
from unittest import mock

from swift.common.swob import Response
from swift.common.utils import FileLikeIter

from storlets.sbus.client import SBusResponse
from storlets.gateway.common.stob import StorletData
from storlets.gateway.gateways.container.gateway import ContainerStorletRequest
from tests.unit import FakeLogger
from tests.unit.gateway.gateways import FakeFileManager


class TestContainerStorletRequest(unittest.TestCase):

    def test_init(self):
        # Java
        storlet_id = 'Storlet-1.0.jar'
        params = {'Param1': 'Value1', 'Param2': 'Value2'}
        metadata = {'MetaKey1': 'MetaValue1', 'MetaKey2': 'MetaValue2'}
        data = StorletData(metadata, iter(StringIO()))

        # with dependencies
        options = {'storlet_main': 'org.openstack.storlet.Storlet',
                   'storlet_dependency': 'dep1,dep2',
                   'storlet_language': 'java',
                   'file_manager': FakeFileManager('storlet', 'dep')}
        dsreq = ContainerStorletRequest(storlet_id, params, data,
                                        options=options)
        self.assertEqual(metadata, dsreq.data.user_metadata)
        self.assertEqual(params, dsreq.params)
        self.assertEqual('Storlet-1.0.jar', dsreq.storlet_id)
        self.assertEqual('org.openstack.storlet.Storlet', dsreq.storlet_main)
        self.assertEqual(['dep1', 'dep2'], dsreq.dependencies)
        self.assertEqual('java', dsreq.storlet_language)
        self.assertIsNone(dsreq.storlet_language_version)

        # without dependencies
        options = {'storlet_main': 'org.openstack.storlet.Storlet',
                   'storlet_language': 'java',
                   'file_manager': FakeFileManager('storlet', 'dep')}
        dsreq = ContainerStorletRequest(storlet_id, params, data,
                                        options=options)
        self.assertEqual(metadata, dsreq.data.user_metadata)
        self.assertEqual(params, dsreq.params)
        self.assertEqual('Storlet-1.0.jar', dsreq.storlet_id)
        self.assertEqual('org.openstack.storlet.Storlet', dsreq.storlet_main)
        self.assertEqual([], dsreq.dependencies)
        self.assertEqual('java', dsreq.storlet_language)
        self.assertIsNone(dsreq.storlet_language_version)

        # storlet_language is not given
        options = {'storlet_main': 'org.openstack.storlet.Storlet',
                   'file_manager': FakeFileManager('storlet', 'dep')}
        with self.assertRaises(ValueError):
            ContainerStorletRequest(storlet_id, params, data, options=options)

        # storlet_main is not given
        options = {'storlet_language': 'java',
                   'file_manager': FakeFileManager('storlet', 'dep')}
        with self.assertRaises(ValueError):
            ContainerStorletRequest(storlet_id, params, data, options=options)

        # file_manager is not given
        options = {'storlet_main': 'org.openstack.storlet.Storlet',
                   'storlet_language': 'java'}
        with self.assertRaises(ValueError):
            ContainerStorletRequest(storlet_id, params, data, options=options)

        # Python
        storlet_id = 'storlet.py'
        params = {'Param1': 'Value1', 'Param2': 'Value2'}
        metadata = {'MetaKey1': 'MetaValue1', 'MetaKey2': 'MetaValue2'}
        data = StorletData(metadata, iter(StringIO()))

        # without language version
        options = {'storlet_main': 'storlet.Storlet',
                   'storlet_language': 'python',
                   'file_manager': FakeFileManager('storlet', 'dep')}
        dsreq = ContainerStorletRequest(storlet_id, params, data,
                                        options=options)
        self.assertEqual(metadata, dsreq.data.user_metadata)
        self.assertEqual(params, dsreq.params)
        self.assertEqual('storlet.py', dsreq.storlet_id)
        self.assertEqual('storlet.Storlet', dsreq.storlet_main)
        self.assertEqual([], dsreq.dependencies)
        self.assertEqual('python', dsreq.storlet_language)
        self.assertIsNone(dsreq.storlet_language_version)

        # with language version
        options = {'storlet_main': 'storlet.Storlet',
                   'storlet_language': 'python',
                   'storlet_language_version': '3.6',
                   'file_manager': FakeFileManager('storlet', 'dep')}
        dsreq = ContainerStorletRequest(storlet_id, params, data,
                                        options=options)
        self.assertEqual(metadata, dsreq.data.user_metadata)
        self.assertEqual(params, dsreq.params)
        self.assertEqual('storlet.py', dsreq.storlet_id)
        self.assertEqual('storlet.Storlet', dsreq.storlet_main)
        self.assertEqual([], dsreq.dependencies)
        self.assertEqual('python', dsreq.storlet_language)
        self.assertEqual('3.6', dsreq.storlet_language_version)

    def test_init_with_range(self):
        storlet_id = 'Storlet-1.0.jar'
        params = {}
        metadata = {}
        data = StorletData(metadata, None, 0)

        options = {'storlet_main': 'org.openstack.storlet.Storlet',
                   'storlet_dependency': 'dep1,dep2',
                   'storlet_language': 'java',
                   'file_manager': FakeFileManager('storlet', 'dep'),
                   'range_start': 1,
                   'range_end': 6}
        dsreq = ContainerStorletRequest(storlet_id, params, data,
                                        options=options)

        self.assertEqual('Storlet-1.0.jar', dsreq.storlet_id)
        self.assertEqual('org.openstack.storlet.Storlet', dsreq.storlet_main)
        self.assertEqual(['dep1', 'dep2'], dsreq.dependencies)
        self.assertEqual('java', dsreq.storlet_language)
        self.assertIsNone(dsreq.storlet_language_version)
        self.assertEqual(1, dsreq.start)
        self.assertEqual(6, dsreq.end)

        options = {'storlet_main': 'org.openstack.storlet.Storlet',
                   'storlet_dependency': 'dep1,dep2',
                   'storlet_language': 'java',
                   'file_manager': FakeFileManager('storlet', 'dep'),
                   'range_start': 0,
                   'range_end': 0}
        dsreq = ContainerStorletRequest(storlet_id, params, data,
                                        options=options)

        self.assertEqual('Storlet-1.0.jar', dsreq.storlet_id)
        self.assertEqual('org.openstack.storlet.Storlet', dsreq.storlet_main)
        self.assertEqual(['dep1', 'dep2'], dsreq.dependencies)
        self.assertEqual('java', dsreq.storlet_language)
        self.assertIsNone(dsreq.storlet_language_version)
        self.assertEqual(0, dsreq.start)
        self.assertEqual(0, dsreq.end)

    def test_has_range(self):
        storlet_id = 'Storlet-1.0.jar'
        params = {}
        metadata = {}
        options = {'storlet_main': 'org.openstack.storlet.Storlet',
                   'storlet_dependency': 'dep1,dep2',
                   'storlet_language': 'java',
                   'file_manager': FakeFileManager('storlet', 'dep')}
        data = StorletData(metadata, None, 0)
        dsreq = ContainerStorletRequest(storlet_id, params, data,
                                        options=options)
        self.assertFalse(dsreq.has_range)

        options = {'storlet_main': 'org.openstack.storlet.Storlet',
                   'storlet_dependency': 'dep1,dep2',
                   'storlet_language': 'java',
                   'file_manager': FakeFileManager('storlet', 'dep'),
                   'range_start': 1,
                   'range_end': 6}
        dsreq = ContainerStorletRequest(storlet_id, params, data,
                                        options=options)
        self.assertTrue(dsreq.has_range)

        options = {'storlet_main': 'org.openstack.storlet.Storlet',
                   'storlet_dependency': 'dep1,dep2',
                   'storlet_language': 'java',
                   'file_manager': FakeFileManager('storlet', 'dep'),
                   'range_start': 0,
                   'range_end': 6}
        dsreq = ContainerStorletRequest(storlet_id, params, data,
                                        options=options)
        self.assertTrue(dsreq.has_range)


class ContainerGatewayTestMixin(object):

    def setUp(self):
        # TODO(takashi): take these values from config file
        self.tempdir = mkdtemp()
        self.sconf = {
            'host_root': self.tempdir,
            'swift_dir': self.tempdir,
            'storlet_timeout': '9',
            'storlet_container': 'storlet',
            'storlet_dependency': 'dependency',
            'reseller_prefix': 'AUTH'
        }
        self.logger = FakeLogger()

        self.storlet_container = self.sconf['storlet_container']
        self.storlet_dependency = self.sconf['storlet_dependency']

        self.version = 'v1'
        self.account = 'AUTH_account'
        self.container = 'container'
        self.obj = 'object'
        self.sobj = 'storlet-1.0.jar'

        self.gateway = self.gateway_class(
            self.sconf, self.logger, self.account)

    def tearDown(self):
        rmtree(self.tempdir)

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

    def _create_proxy_path(self, version, account, container, obj):
        return '/'.join(['', version, account, container, obj])

    def test_check_mandatory_params(self):
        params = {'keyA': 'valueA',
                  'keyB': 'valueB',
                  'keyC': 'valueC'}

        # all mandatory headers are included
        self.gateway_class._check_mandatory_params(
            params, ['keyA', 'keyB'])

        # some of mandatory headers are missing
        with self.assertRaises(ValueError):
            self.gateway_class._check_mandatory_params(
                params, ['keyA', 'KeyD'])

    def test_validate_storlet_registration_java(self):
        # correct name and headers w/ dependency
        obj = 'storlet-1.0.jar'
        params = {'Language': 'java',
                  'Interface-Version': '1.0',
                  'Dependency': 'dep_file',
                  'Object-Metadata': 'no',
                  'Main': 'path.to.storlet.class'}
        self.gateway_class.validate_storlet_registration(params, obj)

        # correct name and headers w/o dependency
        obj = 'storlet-1.0.jar'
        params = {'Language': 'java',
                  'Interface-Version': '1.0',
                  'Object-Metadata': 'no',
                  'Main': 'path.to.storlet.class'}
        self.gateway_class.validate_storlet_registration(params, obj)

        # some header keys are missing
        params = {'Language': 'java',
                  'Interface-Version': '1.0',
                  'Dependency': 'dep_file',
                  'Object-Metadata': 'no'}
        with self.assertRaises(ValueError):
            self.gateway_class.validate_storlet_registration(params, obj)

        # wrong name
        obj = 'storlet.jar'
        params = {'Language': 'java',
                  'Interface-Version': '1.0',
                  'Dependency': 'dep_file',
                  'Object-Metadata': 'no',
                  'Main': 'path.to.storlet.class'}
        with self.assertRaises(ValueError):
            self.gateway_class.validate_storlet_registration(params, obj)

    def test_validate_storlet_registration_python(self):
        # correct name and headers w/ dependency
        obj = 'storlet.py'
        params = {'Language': 'python',
                  'Language-Version': '3.6',
                  'Interface-Version': '1.0',
                  'Dependency': 'dep_file',
                  'Object-Metadata': 'no',
                  'Main': 'storlet.Storlet'}
        self.gateway_class.validate_storlet_registration(params, obj)

        # wrong version
        obj = 'storlet.py'
        params = {'Language': 'python',
                  'Language-Version': '1.7',
                  'Interface-Version': '1.0',
                  'Dependency': 'dep_file',
                  'Object-Metadata': 'no',
                  'Main': 'storlet.Storlet'}
        with self.assertRaises(ValueError):
            self.gateway_class.validate_storlet_registration(params, obj)

        # py2 is no more supported
        obj = 'storlet.py'
        params = {'Language': 'python',
                  'Language-Version': '2.7',
                  'Interface-Version': '1.0',
                  'Dependency': 'dep_file',
                  'Object-Metadata': 'no',
                  'Main': 'storlet.Storlet'}
        with self.assertRaises(ValueError):
            self.gateway_class.validate_storlet_registration(params, obj)

        # wrong name
        obj = 'storlet.pyfoo'
        params = {'Language': 'python',
                  'Interface-Version': '1.0',
                  'Dependency': 'dep_file',
                  'Object-Metadata': 'no',
                  'Main': 'storlet.Storlet'}
        with self.assertRaises(ValueError):
            self.gateway_class.validate_storlet_registration(params, obj)

        # wrong main class
        obj = 'storlet.py'
        params = {'Language': 'python',
                  'Interface-Version': '1.0',
                  'Dependency': 'dep_file',
                  'Object-Metadata': 'no',
                  'Main': 'another_storlet.Storlet'}
        with self.assertRaises(ValueError):
            self.gateway_class.validate_storlet_registration(params, obj)

        obj = 'storlet.py'
        params = {'Language': 'python',
                  'Interface-Version': '1.0',
                  'Dependency': 'dep_file',
                  'Object-Metadata': 'no',
                  'Main': 'storlet'}
        with self.assertRaises(ValueError):
            self.gateway_class.validate_storlet_registration(params, obj)

        obj = 'storlet.py'
        params = {'Language': 'python',
                  'Interface-Version': '1.0',
                  'Dependency': 'dep_file',
                  'Object-Metadata': 'no',
                  'Main': 'storlet.foo.Storlet'}
        with self.assertRaises(ValueError):
            self.gateway_class.validate_storlet_registration(params, obj)

    def test_validate_storlet_registration_not_suppoeted(self):
        # unsupported language
        obj = 'storlet.foo'
        params = {'Language': 'bar',
                  'Interface-Version': '1.0',
                  'Dependency': 'dep_file',
                  'Object-Metadata': 'no',
                  'Main': 'path.to.storlet.class'}
        with self.assertRaises(ValueError):
            self.gateway_class.validate_storlet_registration(params, obj)

        # same name for storlet and dependency
        obj = 'storlet-1.0.jar'
        params = {'Language': 'java',
                  'Interface-Version': '1.0',
                  'Dependency': 'storlet-1.0.jar',
                  'Object-Metadata': 'no',
                  'Main': 'path.to.storlet.class'}
        with self.assertRaises(ValueError):
            self.gateway_class.validate_storlet_registration(params, obj)

        # duplicated name in dependencies
        obj = 'storlet-1.0.jar'
        params = {'Language': 'java',
                  'Interface-Version': '1.0',
                  'Dependency': 'dep_file,dep_file',
                  'Object-Metadata': 'no',
                  'Main': 'path.to.storlet.class'}
        with self.assertRaises(ValueError):
            self.gateway_class.validate_storlet_registration(params, obj)

    def test_validate_dependency_registration(self):
        # w/o dependency parameter
        obj = 'dep_file'
        params = {'Dependency-Version': '1.0'}
        self.gateway_class.validate_dependency_registration(params, obj)

        # w/ correct dependency parameter
        params = {
            'Dependency-Permissions': '755',
            'Dependency-Version': '1.0'}
        self.gateway_class.validate_dependency_registration(params, obj)

        # w/ wrong dependency parameter
        params = {
            'Dependency-Permissions': '400',
            'Dependency-Version': '1.0'}
        with self.assertRaises(ValueError):
            self.gateway_class.validate_dependency_registration(params, obj)

        # w/ invalid dependency parameter
        params = {
            'Dependency-Permissions': 'foo',
            'Dependency-Version': '1.0'}
        with self.assertRaises(ValueError):
            self.gateway_class.validate_dependency_registration(params, obj)
        params = {
            'Dependency-Permissions': '888',
            'Dependency-Version': '1.0'}
        with self.assertRaises(ValueError):
            self.gateway_class.validate_dependency_registration(params, obj)

    def _test_invocation_flow(self, extra_sources=None):
        extra_sources = extra_sources or []
        options = {'generate_log': False,
                   'scope': 'AUTH_account',
                   'storlet_main': 'org.openstack.storlet.Storlet',
                   'storlet_dependency': 'dep1,dep2',
                   'storlet_language': 'java',
                   'file_manager': FakeFileManager('storlet', 'dep')}

        data = StorletData(
            user_metadata={},
            data_iter=iter('body'))
        st_req = ContainerStorletRequest(
            storlet_id=self.sobj,
            params={},
            data=data,
            options=options)

        # TODO(kota_): need more efficient way for emuration of return value
        # from SDaemon
        value_generator = iter([
            # first, we get metadata json
            json.dumps({'metadata': 'return'}),
            # then we get object data
            'something', '',
        ])

        def mock_read(fd, size):
            try:
                value = next(value_generator)
            except StopIteration:
                raise Exception('called more then expected')
            # NOTE(takashi): Make sure that we return bytes in PY3
            return value.encode('utf-8')

        def mock_close(fd):
            pass

        called_fd_and_bodies = []
        invocation_protocol = \
            'storlets.gateway.gateways.container.runtime.' \
            'StorletInvocationProtocol._write_input_data'

        def mock_writer(self, fd, app_iter):
            body = ''
            for chunk in app_iter:
                body += chunk
            called_fd_and_bodies.append((fd, body))

        # prepare nested mock patch
        # SBus -> mock SBus.send() for container communication
        # os.read -> mock reading the file descriptor from container
        # select.select -> mock fd communication which can be readable
        @mock.patch('storlets.gateway.gateways.container.runtime.SBusClient')
        @mock.patch('storlets.gateway.gateways.container.runtime.os.read',
                    mock_read)
        @mock.patch('storlets.gateway.gateways.container.runtime.os.close',
                    mock_close)
        @mock.patch('storlets.gateway.gateways.container.runtime.select.'
                    'select',
                    lambda r, w, x, timeout=None: (r, w, x))
        @mock.patch('storlets.gateway.common.stob.os.read', mock_read)
        @mock.patch(invocation_protocol, mock_writer)
        def test_invocation_flow(client):
            client.ping.return_value = SBusResponse(True, 'OK')
            client.stop_daemon.return_value = SBusResponse(True, 'OK')
            client.start_daemon.return_value = SBusResponse(True, 'OK')
            client.execute.return_value = SBusResponse(True, 'OK', 'someid')

            sresp = self.gateway.invocation_flow(st_req)
            eventlet.sleep(0.1)
            file_like = FileLikeIter(sresp.data.data_iter)
            self.assertEqual(b'something', file_like.read())

        # I hate the decorator to return an instance but to track current
        # implementation, we have to make a mock class for this. Need to fix.

        class MockFileManager(object):
            def get_storlet(self, req):
                return BytesIO(b'mock'), None

            def get_dependency(self, req):
                return BytesIO(b'mock'), None

        st_req.file_manager = MockFileManager()
        st_req.extra_data_list = extra_sources

        test_invocation_flow()

        # ensure st_req.app_iter is drawn
        self.assertRaises(StopIteration, next, st_req.data.data_iter)
        expected_mock_writer_calls = len(extra_sources) + 1
        self.assertEqual(expected_mock_writer_calls,
                         len(called_fd_and_bodies))
        self.assertEqual('body', called_fd_and_bodies[0][1])
        return called_fd_and_bodies

    def test_invocation_flow(self):
        self._test_invocation_flow()

    def test_invocation_flow_with_extra_sources(self):
        data_sources = []

        def generate_extra_data():
            sw_resp = Response(
                app_iter=iter(['This is a response body']), status=200)

            data = StorletData(
                user_metadata={},
                data_iter=sw_resp.app_iter)
            data_sources.append(sw_resp.app_iter)
            return data

        extra_data = generate_extra_data()
        mock_calls = self._test_invocation_flow(extra_sources=[extra_data])
        self.assertEqual('This is a response body', mock_calls[1][1])

        # run all existing eventlet threads
        for app_iter in data_sources:
            # ensure all app_iters are drawn
            self.assertRaises(StopIteration, next, app_iter)


if __name__ == '__main__':
    unittest.main()
