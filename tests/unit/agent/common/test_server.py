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
import mock
import json
import unittest

from storlets.sbus import command as sbus_cmd
from storlets.sbus.file_description import SBUS_FD_SERVICE_OUT
from storlets.sbus.datagram import SBusFileDescriptor, SBusServiceDatagram
from storlets.agent.common.server import EXIT_SUCCESS, command_handler, \
    CommandResponse, CommandFailure, CommandSuccess, SBusServer
from tests.unit import FakeLogger


class TestCommandResponse(unittest.TestCase):
    def test_init(self):
        resp = CommandResponse(True, 'ok')
        self.assertTrue(resp.status)
        self.assertEqual('ok', resp.message)
        self.assertTrue(resp.iterable)

        resp = CommandResponse(False, 'error', False)
        self.assertFalse(resp.status)
        self.assertEqual('error', resp.message)
        self.assertFalse(resp.iterable)

    def test_report_message(self):
        resp = CommandResponse(True, 'msg', True)
        self.assertEqual({'status': True, 'message': 'msg'},
                         json.loads(resp.report_message))


class TestCommandSuccess(unittest.TestCase):
    def test_init(self):
        resp = CommandSuccess('ok')
        self.assertTrue(resp.status)
        self.assertEqual('ok', resp.message)
        self.assertTrue(resp.iterable)


class TestCommandFailure(unittest.TestCase):
    def test_init(self):
        resp = CommandFailure('error')
        self.assertFalse(resp.status)
        self.assertEqual('error', resp.message)
        self.assertTrue(resp.iterable)


class TestCommandHandler(unittest.TestCase):
    def test_command_handler(self):

        @command_handler
        def test_func():
            pass

        self.assertTrue(hasattr(test_func, 'is_command_handler'))
        self.assertTrue(test_func.is_command_handler)


class TestSBusServer(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.sbus_path = 'path/to/pipe'
        self.server = SBusServer(self.sbus_path, self.logger)

    def test_get_handler(self):
        # halt
        self.assertEqual(
            self.server.halt, self.server.get_handler(sbus_cmd.SBUS_CMD_HALT))
        # ping
        self.assertEqual(
            self.server.ping, self.server.get_handler(sbus_cmd.SBUS_CMD_PING))

        # daemon status is defined as sbus command, but the command is not
        # implemented in SBusServer
        with self.assertRaises(ValueError):
            self.server.get_handler('SBUS_CMD_DAEMON_STATUS')

        # invalid command
        with self.assertRaises(ValueError):
            self.server.get_handler('FOO')
        # unknown command
        with self.assertRaises(ValueError):
            self.server.get_handler('SBUS_CMD_UNKNOWN')


def create_fake_sbus_class(scenario):
    """
    :param scenario: a list of tuples [(command, return_value)]
    """
    class FakeSBus(object):
        """
        Fake SBus communication according feeded scenario.
        The scenario must be ordered by calls
        """
        def __init__(self):
            self.scenario = scenario
            self.called = []

        def _get_fake_response(self, command, *args):
            self.called.append((command, args))
            try:
                ret_val = self.scenario.pop(0)
            except IndexError:
                raise AssertionError(
                    'Daemon calls SBus command more than expected,'
                    ' need "%s" call at least' % command)

            if ret_val[0] != command:
                raise AssertionError(
                    "Expected scenario doesn't happen, actual daemon calls %s"
                    "for SBus but %d is expected" % (command, ret_val[0]))
            return ret_val[1]

        def listen(self, fd):
            return self._get_fake_response('listen', fd)

        def command(self):
            return self._get_fake_response('command')

        def create(self, sbus_path):
            return self._get_fake_response('create', sbus_path)

        def receive(self, fd):
            return self._get_fake_response('receive', fd)

    return FakeSBus


class TestSBusServerMain(unittest.TestCase):

    def _get_test_server(self):
        return SBusServer(self.sbus_path, self.logger)

    def setUp(self):
        self.logger = FakeLogger()
        self.sbus_path = 'fake_path'
        self.server = self._get_test_server()

    def _test_main_loop_stop(self, stop_command):
        sfds = [SBusFileDescriptor(SBUS_FD_SERVICE_OUT, 1)]
        scenario = [
            ('create', 1),
            ('listen', 1),
            ('receive', SBusServiceDatagram(command=stop_command, sfds=sfds,
                                            params=None, task_id=None)),
        ]

        fake_sbus_class = create_fake_sbus_class(scenario)
        with mock.patch('storlets.agent.common.server.SBus', fake_sbus_class):
            with mock.patch('os.fdopen'):
                ret = self.server.main_loop()

        self.assertEqual(EXIT_SUCCESS, ret)
        # sanity for no error and no warning
        self.assertEqual([], self.logger.get_log_lines('error'))
        self.assertEqual([], self.logger.get_log_lines('warn'))


if __name__ == '__main__':
    unittest.main()
