# Copyright (c) 2015-2016 OpenStack Foundation
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

import json
import unittest
import sbus.file_description as sbus_fd
from sbus.datagram import FDMetadata, SBusDatagram, \
    ClientSBusOutDatagram, ServerSBusInDatagram


class TestFDMetadata(unittest.TestCase):
    def setUp(self):
        pass

    def test_to_dict(self):
        md = FDMetadata('MYTYPE', {'storlets_key': 'storlets_value'},
                        {'storage_key': 'storage_value'})
        self.assertEqual({'storlets': {'type': 'MYTYPE',
                                       'storlets_key': 'storlets_value'},
                          'storage': {'storage_key': 'storage_value'}},
                         md.to_dict())

    def test_from_dict(self):
        md = FDMetadata.from_dict(
            {'storlets': {'type': 'MYTYPE',
                          'storlets_key': 'storlets_value'},
             'storage': {'storage_key': 'storage_value'}})
        self.assertEqual('MYTYPE', md.fdtype)
        self.assertEqual({'storlets_key': 'storlets_value'},
                         md.storlets_metadata)
        self.assertEqual({'storage_key': 'storage_value'},
                         md.storage_metadata)


class TestSBusDatagram(unittest.TestCase):
    def setUp(self):
        self.command = 'COMMAND'
        self.types = [sbus_fd.SBUS_FD_SERVICE_OUT,
                      sbus_fd.SBUS_FD_OUTPUT_OBJECT,
                      sbus_fd.SBUS_FD_OUTPUT_OBJECT,
                      sbus_fd.SBUS_FD_OUTPUT_OBJECT_METADATA,
                      sbus_fd.SBUS_FD_OUTPUT_OBJECT_METADATA,
                      sbus_fd.SBUS_FD_OUTPUT_TASK_ID,
                      sbus_fd.SBUS_FD_LOGGER,
                      sbus_fd.SBUS_FD_INPUT_OBJECT,
                      sbus_fd.SBUS_FD_INPUT_OBJECT]
        self.fds = []
        self.metadata = []
        for i in xrange(len(self.types)):
            self.fds.append(i + 1)
            self.metadata.append(
                FDMetadata(self.types[i],
                           {'key%d' % i: 'value%d' % i},
                           {'skey%d' % i: 'svalue%d' % i}).to_dict())
        self.params = {'param1': 'paramvalue1'}
        self.task_id = 'id'
        self.dtg = self._create_datagram()

    def _create_datagram(self):
        return SBusDatagram(
            self.command, self.fds, self.metadata, self.params,
            self.task_id)

    def test_init(self):
        self.assertEqual(self.command, self.dtg.command)
        self.assertEqual(self.fds, self.dtg.fds)
        self.assertEqual(self.metadata, self.dtg.metadata)
        self.assertEqual(self.params, self.dtg.params)
        self.assertEqual(self.task_id, self.dtg.task_id)

    def test_num_fds(self):
        self.assertEqual(len(self.types), self.dtg.num_fds)

    def test_cmd_params(self):
        self.assertEqual({'command': self.command,
                          'params': self.params,
                          'task_id': self.task_id},
                         self.dtg.cmd_params)


class TestClientSBusOutDatagram(TestSBusDatagram):
    def setUp(self):
        super(TestClientSBusOutDatagram, self).setUp()

    def _create_datagram(self):
        return ClientSBusOutDatagram(
            self.command, self.fds, self.metadata, self.params,
            self.task_id)

    def test_serialized_metadata(self):
        self.assertEqual(self.metadata,
                         json.loads(self.dtg.serialized_metadata))

    def test_serialized_cmd_params(self):
        res = {'command': self.command,
               'params': self.params,
               'task_id': self.task_id}
        self.assertEqual(res,
                         json.loads(self.dtg.serialized_cmd_params))

    def test_create_service_datagram(self):
        dtg = ClientSBusOutDatagram.create_service_datagram(
            self.command, 1, self.params, self.task_id)
        self.assertEqual(self.params, dtg.params)
        self.assertEqual(self.command, dtg.command)
        self.assertEqual(self.task_id, dtg.task_id)
        self.assertEqual([1], dtg.fds)
        self.assertEqual([{'storlets': {'type': sbus_fd.SBUS_FD_SERVICE_OUT},
                           'storage': {}}], dtg.metadata)

        dtg = ClientSBusOutDatagram.create_service_datagram(
            self.command, 1)
        self.assertIsNone(dtg.params)
        self.assertEqual(self.command, dtg.command)
        self.assertIsNone(dtg.task_id)
        self.assertEqual([1], dtg.fds)
        self.assertEqual([{'storlets': {'type': sbus_fd.SBUS_FD_SERVICE_OUT},
                           'storage': {}}], dtg.metadata)


class TestServerSBusInOutDatagram(TestSBusDatagram):
    def setUp(self):
        super(TestServerSBusInOutDatagram, self).setUp()

    def _create_datagram(self):
        md_json = json.dumps(self.metadata)
        cmd_params = {'command': self.command,
                      'params': self.params,
                      'task_id': self.task_id}
        cmd_params = json.dumps(cmd_params)
        return ServerSBusInDatagram(
            self.fds, md_json, cmd_params)

    def test_find_fds(self):
        self.assertEqual(
            [1], self.dtg._find_fds(sbus_fd.SBUS_FD_SERVICE_OUT))
        self.assertEqual(
            [2, 3], self.dtg._find_fds(sbus_fd.SBUS_FD_OUTPUT_OBJECT))
        self.assertEqual(
            [], self.dtg._find_fds('DUMMY_TYPE'))

    def test_find_fd(self):
        self.assertEqual(
            1, self.dtg._find_fd(sbus_fd.SBUS_FD_SERVICE_OUT))
        self.assertEqual(
            2, self.dtg._find_fd(sbus_fd.SBUS_FD_OUTPUT_OBJECT))
        self.assertIsNone(
            self.dtg._find_fd('DUMMY_TYPE'))

    def test_service_out_fd(self):
        self.assertEqual(1, self.dtg.service_out_fd)

    def test_object_out_fds(self):
        self.assertEqual([2, 3], self.dtg.object_out_fds)

    def test_object_metadata_out_fds(self):
        self.assertEqual([4, 5], self.dtg.object_metadata_out_fds)

    def test_task_id_out_fd(self):
        self.assertEqual(6, self.dtg.task_id_out_fd)

    def test_logger_out_fd(self):
        self.assertEqual(7, self.dtg.logger_out_fd)

    def test_object_in_fds(self):
        self.assertEqual([8, 9], self.dtg.object_in_fds)


if __name__ == '__main__':
    unittest.main()
