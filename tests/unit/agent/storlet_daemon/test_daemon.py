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
import unittest
import eventlet
import mock
from storlets.agent.daemon.manager import (
    Daemon, EXIT_SUCCESS, StorletDaemonException)
from storlets.sbus.datagram import FDMetadata, SBusServiceDatagram
from storlets.sbus.file_description import SBUS_FD_SERVICE_OUT
import storlets.sbus.command

from tests.unit import FakeLogger


class FakeModule(object):
    FakeClass = mock.MagicMock


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


class TestStorletDaemon(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()
        self.pile = eventlet.greenpool.GreenPile(1)

    def test_invalid_module_name(self):
        for module_name in ('only_module',
                            'OnlyClass',
                            'nested.module.Class',
                            1, None, True, False):
            self._test_invalid_module_name(module_name)

    def _test_invalid_module_name(self, module_name):
        with self.assertRaises(ValueError) as cm:
            Daemon(module_name, 'fake_path', self.logger, 16)
        self.assertEqual('Invalid storlet name %s' % module_name,
                         cm.exception.message)

    def test_module_not_found(self):
        with self.assertRaises(StorletDaemonException) as cm:
            Daemon('nomodule.Nothing', 'fake_path', self.logger, 16)
        self.assertEqual('Failed to load storlet nomodule.Nothing',
                         cm.exception.message)

    def _test_main_loop_stop(self, stop_command):
        with mock.patch('__builtin__.__import__') as fake_import:
            fake_import.return_value = FakeModule()
            daemon = Daemon(
                'fakeModule.FakeClass', 'fake_path', self.logger, 16)
        metadata = [FDMetadata(SBUS_FD_SERVICE_OUT).to_dict()]
        scenario = [
            ('create', 1),
            ('listen', 1),
            ('receive', SBusServiceDatagram(command=stop_command, fds=[1],
                                            metadata=metadata,
                                            params=None, task_id=None)),
        ]

        fake_sbus_class = create_fake_sbus_class(scenario)
        with mock.patch(
                'storlets.agent.daemon.manager.SBus', fake_sbus_class):
            with mock.patch('os.fdopen'):
                self.pile.spawn(daemon.main_loop)
                eventlet.sleep()
                ret = [ret for ret in self.pile][0]

        self.assertEqual(EXIT_SUCCESS, ret)
        # sanity for no error and no warning
        self.assertEqual([], self.logger.get_log_lines('error'))
        self.assertEqual([], self.logger.get_log_lines('warn'))

    def test_main_loop_successful_stop(self):
        # SBUS_CMD_HALT is for working to stop requested from
        # storlet_middleware
        self._test_main_loop_stop(storlets.sbus.command.SBUS_CMD_HALT)

    def test_main_loop_canceled_stop(self):
        # SBUS_CMD_CANCEL is for working to stop from sort of daemon
        # management tools
        # TODO(kota_): SBUS_CMD_CANCEL has more tasks to do for cleanup
        # so need more assertions.
        self._test_main_loop_stop(storlets.sbus.command.SBUS_CMD_CANCEL)


if __name__ == '__main__':
    unittest.main()
