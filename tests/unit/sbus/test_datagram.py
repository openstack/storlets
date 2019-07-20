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
import storlets.sbus.file_description as sbus_fd
from storlets.sbus.datagram import SBusFileDescriptor, SBusDatagram, \
    SBusServiceDatagram, SBusExecuteDatagram, build_datagram, \
    build_datagram_from_raw_message
from storlets.sbus.command import SBUS_CMD_PING, SBUS_CMD_EXECUTE

ALL_FDTYPES = [
    sbus_fd.SBUS_FD_INPUT_OBJECT, sbus_fd.SBUS_FD_OUTPUT_OBJECT,
    sbus_fd.SBUS_FD_OUTPUT_OBJECT_METADATA,
    sbus_fd.SBUS_FD_OUTPUT_OBJECT_AND_METADATA,
    sbus_fd.SBUS_FD_LOGGER, sbus_fd.SBUS_FD_OUTPUT_CONTAINER,
    sbus_fd.SBUS_FD_SERVICE_OUT,
]


class TestSBusFileDescriptor(unittest.TestCase):
    def test_metadata(self):
        fd = SBusFileDescriptor(
            'MYTYPE', 1, {'storlets_key': 'storlets_value'},
            {'storage_key': 'storage_value'})
        self.assertEqual(
            {'storlets': {'type': 'MYTYPE', 'storlets_key': 'storlets_value'},
             'storage': {'storage_key': 'storage_value'}},
            fd.metadata)

    def test_from_fileno_and_metadata_dict(self):
        fd = SBusFileDescriptor.from_fileno_and_metadata_dict(
            1,
            {'storlets': {'type': 'MYTYPE', 'storlets_key': 'storlets_value'},
             'storage': {'storage_key': 'storage_value'}})
        self.assertEqual(1, fd.fileno)
        self.assertEqual('MYTYPE', fd.fdtype)
        self.assertEqual({'storlets_key': 'storlets_value'},
                         fd.storlets_metadata)
        self.assertEqual({'storage_key': 'storage_value'},
                         fd.storage_metadata)


class TestSBusDatagram(unittest.TestCase):
    def test_check_required_fdtypes_not_implemented(self):
        # SBusDatagram designed not to be called independently
        with self.assertRaises(NotImplementedError) as err:
            SBusDatagram('', [], [])
        self.assertEqual(
            'SBusDatagram class should not be initialized as bare',
            err.exception.args[0])

    def test_invalid_child_class_definition(self):
        # no definition for _required_fdtypes
        class InvalidSBusDatagram(SBusDatagram):
            pass

        with self.assertRaises(NotImplementedError) as err:
            InvalidSBusDatagram('', [], [])
        self.assertEqual(
            'SBusDatagram class should define _required_fdtypes',
            err.exception.args[0])


class SBusDatagramTestMixin(object):
    def setUp(self):
        self.params = {'param1': 'paramvalue1'}
        self.task_id = 'id'
        self.dtg = self._test_class(self.command, self.sfds,
                                    self.params, self.task_id)

    def test_init(self):
        self.assertEqual(self.command, self.dtg.command)
        self.assertEqual(self.sfds, self.dtg.sfds)
        self.assertEqual(self.params, self.dtg.params)
        self.assertEqual(self.task_id, self.dtg.task_id)

    def test_num_fds(self):
        self.assertEqual(len(self.fdtypes), self.dtg.num_fds)

    def test_cmd_params(self):
        self.assertEqual({'command': self.command,
                          'params': self.params,
                          'task_id': self.task_id},
                         self.dtg.cmd_params)

    def test_serialized_cmd_params(self):
        res = {'command': self.command,
               'params': self.params,
               'task_id': self.task_id}
        self.assertEqual(res, json.loads(self.dtg.serialized_cmd_params))

    def test_check_required_fdtypes_mismatch(self):
        invalid_fdtypes_list = (
            [],  # empty list
            ['Invalid'] + self.fdtypes,  # invalid type inserted at the first
            # TODO(kota_): we may want *strict* check (not only checking first
            #              N items.
        )

        for invalid_fdtypes in invalid_fdtypes_list:
            with self.assertRaises(ValueError) as cm:
                self.dtg._check_required_fdtypes(invalid_fdtypes)
            self.assertTrue(cm.exception.args[0].startswith(
                'Fd type mismatch given_fdtypes'))

    def test_find_fds(self):
        # prepare all fd types and then pop out in the loop below
        not_in_fdtypes = ALL_FDTYPES[:]
        # N.B. fd should start from 1 (not 0), really?
        for index, fdtype in enumerate(self.fdtypes, 1):
            found_fds = self.dtg._find_fds(fdtype)
            # at least 1 fd should be found
            self.assertTrue(found_fds)
            # and the index is in the types
            self.assertIn(index, found_fds)

            if fdtype in not_in_fdtypes:
                # N.B. ALL_FDTYPES should be unique list
                not_in_fdtypes.remove(fdtype)

        # sanity, not a fd type results in []
        self.assertEqual([], self.dtg._find_fds('DUMMY_TYPE'))

        # sanity, no other types are found
        for fdtype in not_in_fdtypes:
            self.assertEqual([], self.dtg._find_fds(fdtype))

    def test_find_fd(self):
        # prepare all fd types and then pop out in the loop below
        not_in_fdtypes = ALL_FDTYPES[:]
        # N.B. fd should start from 1 (not 0), really?
        for index, fdtype in enumerate(self.fdtypes, 1):
            found_fd = self.dtg._find_fd(fdtype)
            # at least 1 fd should be found
            self.assertEqual(index, found_fd)

            if fdtype in not_in_fdtypes:
                # N.B. ALL_FDTYPES should be unique list
                not_in_fdtypes.remove(fdtype)

        # sanity, not a fd type results in None
        self.assertIsNone(self.dtg._find_fd('DUMMY_TYPE'))

        # sanity, no other types are found
        for fdtype in not_in_fdtypes:
            self.assertIsNone(self.dtg._find_fd(fdtype))


class TestSBusServiceDatagram(SBusDatagramTestMixin, unittest.TestCase):
    _test_class = SBusServiceDatagram

    def setUp(self):
        self.command = 'SBUS_CMD_TEST'
        self.fdtypes = [sbus_fd.SBUS_FD_SERVICE_OUT]
        self.sfds = [SBusFileDescriptor(sbus_fd.SBUS_FD_SERVICE_OUT, 1)]
        super(TestSBusServiceDatagram, self).setUp()

    def test_service_out_fd(self):
        self.assertEqual(1, self.dtg.service_out_fd)


class TestSBusExecuteDatagram(SBusDatagramTestMixin, unittest.TestCase):
    _test_class = SBusExecuteDatagram

    def setUp(self):
        self.command = SBUS_CMD_EXECUTE
        self.fdtypes = [sbus_fd.SBUS_FD_SERVICE_OUT,
                        sbus_fd.SBUS_FD_INPUT_OBJECT,
                        sbus_fd.SBUS_FD_OUTPUT_OBJECT,
                        sbus_fd.SBUS_FD_OUTPUT_OBJECT_METADATA,
                        sbus_fd.SBUS_FD_LOGGER]
        self.sfds = [SBusFileDescriptor(
            fdtype, i + 1,
            {'key%d' % i: 'value%d' % i},
            {'skey%d' % i: 'svalue%d' % i})
            for i, fdtype in enumerate(self.fdtypes)]
        super(TestSBusExecuteDatagram, self).setUp()

    def test_init_extra_sources(self):
        fdtypes = [sbus_fd.SBUS_FD_SERVICE_OUT,
                   sbus_fd.SBUS_FD_INPUT_OBJECT,
                   sbus_fd.SBUS_FD_OUTPUT_OBJECT,
                   sbus_fd.SBUS_FD_OUTPUT_OBJECT_METADATA,
                   sbus_fd.SBUS_FD_LOGGER,
                   sbus_fd.SBUS_FD_INPUT_OBJECT,
                   sbus_fd.SBUS_FD_INPUT_OBJECT,
                   sbus_fd.SBUS_FD_INPUT_OBJECT]
        fds = [SBusFileDescriptor(fdtype, i + 1,
               {'key%d' % i: 'value%d' % i},
               {'skey%d' % i: 'svalue%d' % i})
               for i, fdtype in enumerate(fdtypes)]
        dtg = self._test_class(
            self.command, fds, self.params, self.task_id)
        self.assertEqual(fdtypes, [sfd.fdtype for sfd in dtg.sfds])
        self.assertEqual(self.params, dtg.params)
        self.assertEqual(self.task_id, dtg.task_id)

    def test_service_out_fd(self):
        self.assertEqual(1, self.dtg.service_out_fd)

    def test_invocation_fds(self):
        self.assertEqual([2, 3, 4, 5], self.dtg.invocation_fds)

    def test_object_out_fds(self):
        self.assertEqual([3], self.dtg.object_out_fds)

    def test_object_metadata_out_fds(self):
        self.assertEqual([4], self.dtg.object_metadata_out_fds)

    def test_logger_out_fd(self):
        self.assertEqual(5, self.dtg.logger_out_fd)

    def test_object_in_fds(self):
        self.assertEqual([2], self.dtg.object_in_fds)

    def test_check_required_fdtypes_reverse_order_failed(self):
        fdtypes = self.fdtypes[:]
        fdtypes.reverse()  # reverse order
        with self.assertRaises(ValueError) as cm:
            self.dtg._check_required_fdtypes(fdtypes)
        self.assertTrue(
            cm.exception.args[0].startswith('Fd type mismatch given_fdtypes'))


class TestBuildDatagram(unittest.TestCase):

    def test_build_datagram(self):
        # SBusServiceDatagram scenario
        command = SBUS_CMD_PING
        fdtypes = [sbus_fd.SBUS_FD_SERVICE_OUT]
        fds = [SBusFileDescriptor(sbus_fd.SBUS_FD_SERVICE_OUT, 1)]
        params = {'param1': 'paramvalue1'}
        task_id = 'id'

        dtg = build_datagram(command, fds, params, task_id)

        self.assertIsInstance(dtg, SBusServiceDatagram)
        self.assertEqual(command, dtg.command)
        self.assertEqual(fdtypes, [sfd.fdtype for sfd in dtg.sfds])
        self.assertEqual(params, dtg.params)
        self.assertEqual(task_id, dtg.task_id)

        # SBusExecuteDatagram scenario
        command = SBUS_CMD_EXECUTE
        fdtypes = [sbus_fd.SBUS_FD_SERVICE_OUT,
                   sbus_fd.SBUS_FD_INPUT_OBJECT,
                   sbus_fd.SBUS_FD_OUTPUT_OBJECT,
                   sbus_fd.SBUS_FD_OUTPUT_OBJECT_METADATA,
                   sbus_fd.SBUS_FD_LOGGER,
                   sbus_fd.SBUS_FD_INPUT_OBJECT,
                   sbus_fd.SBUS_FD_INPUT_OBJECT,
                   sbus_fd.SBUS_FD_INPUT_OBJECT]
        fds = [SBusFileDescriptor(fdtype, i + 1,
               {'key%d' % i: 'value%d' % i},
               {'skey%d' % i: 'svalue%d' % i})
               for i, fdtype in enumerate(fdtypes)]
        params = {'param1': 'paramvalue1'}
        task_id = 'id'

        dtg = build_datagram(command, fds, params, task_id)

        self.assertIsInstance(dtg, SBusExecuteDatagram)
        self.assertEqual(command, dtg.command)
        self.assertEqual(fdtypes, [sfd.fdtype for sfd in dtg.sfds])
        self.assertEqual(params, dtg.params)
        self.assertEqual(task_id, dtg.task_id)

    def test_build_datagram_from_raw_message(self):
        # SBusServiceDatagram scenario
        command = SBUS_CMD_PING
        fdtypes = [sbus_fd.SBUS_FD_SERVICE_OUT]
        fds = [SBusFileDescriptor(sbus_fd.SBUS_FD_SERVICE_OUT, 1)]
        params = {'param1': 'paramvalue1'}
        task_id = 'id'
        cmd_params = {'command': command, 'params': params, 'task_id': task_id}

        str_metadata = json.dumps([fd.metadata for fd in fds])
        str_cmd_params = json.dumps(cmd_params)
        dtg = build_datagram_from_raw_message(fds, str_metadata,
                                              str_cmd_params)

        self.assertIsInstance(dtg, SBusServiceDatagram)
        self.assertEqual(command, dtg.command)
        self.assertEqual(fdtypes, [sfd.fdtype for sfd in dtg.sfds])
        self.assertEqual(params, dtg.params)
        self.assertEqual(task_id, dtg.task_id)

        # SBusExecuteDatagram scenario
        command = SBUS_CMD_EXECUTE
        fdtypes = [sbus_fd.SBUS_FD_SERVICE_OUT,
                   sbus_fd.SBUS_FD_INPUT_OBJECT,
                   sbus_fd.SBUS_FD_OUTPUT_OBJECT,
                   sbus_fd.SBUS_FD_OUTPUT_OBJECT_METADATA,
                   sbus_fd.SBUS_FD_LOGGER,
                   sbus_fd.SBUS_FD_INPUT_OBJECT,
                   sbus_fd.SBUS_FD_INPUT_OBJECT,
                   sbus_fd.SBUS_FD_INPUT_OBJECT]
        fds = [SBusFileDescriptor(fdtype, i + 1,
               {'key%d' % i: 'value%d' % i},
               {'skey%d' % i: 'svalue%d' % i})
               for i, fdtype in enumerate(fdtypes)]
        params = {'param1': 'paramvalue1'}
        task_id = 'id'
        cmd_params = {'command': command, 'params': params, 'task_id': task_id}

        str_metadata = json.dumps([fd.metadata for fd in fds])
        str_cmd_params = json.dumps(cmd_params)
        dtg = build_datagram_from_raw_message(fds, str_metadata,
                                              str_cmd_params)

        self.assertIsInstance(dtg, SBusExecuteDatagram)
        self.assertEqual(command, dtg.command)
        self.assertEqual(fdtypes, [sfd.fdtype for sfd in dtg.sfds])
        self.assertEqual(params, dtg.params)
        self.assertEqual(task_id, dtg.task_id)


if __name__ == '__main__':
    unittest.main()
