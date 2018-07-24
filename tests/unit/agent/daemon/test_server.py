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
import unittest

from storlets.sbus import command as sbus_cmd
from storlets.agent.daemon.server import StorletDaemon, StorletDaemonLoadError

from tests.unit import FakeLogger
from tests.unit.agent.common import test_server


class FakeModule(object):
    FakeClass = mock.MagicMock


class TestStorletDaemon(unittest.TestCase):
    def setUp(self):
        self.logger = FakeLogger()

    def test_invalid_module_name(self):
        for module_name in ('only_module',
                            'OnlyClass',
                            'nested.module.Class',
                            1, None, True, False):
            self._test_invalid_module_name(module_name)

    def _test_invalid_module_name(self, module_name):
        with self.assertRaises(ValueError) as cm:
            StorletDaemon(module_name, 'fake_path', self.logger, 16)
        self.assertEqual('Invalid storlet name %s' % module_name,
                         cm.exception.args[0])

    def test_module_not_found(self):
        with self.assertRaises(StorletDaemonLoadError) as cm:
            StorletDaemon('nomodule.Nothing', 'fake_path', self.logger, 16)
        self.assertEqual('Failed to load storlet nomodule.Nothing',
                         cm.exception.args[0])


class TestStorletDaemonMain(test_server.TestSBusServerMain):

    def _get_test_server(self):
        with mock.patch('importlib.import_module') as fake_import:
            fake_import.return_value = FakeModule()
            server = StorletDaemon(
                'fakeModule.FakeClass', self.sbus_path, self.logger, 16)
        return server

    def test_main_loop_successful_stop(self):
        # SBUS_CMD_HALT is for working to stop requested from
        # storlet_middleware
        self._test_main_loop_stop(sbus_cmd.SBUS_CMD_HALT)

    def test_main_loop_canceled_stop(self):
        # SBUS_CMD_CANCEL is for working to stop from sort of daemon
        # management tools
        # TODO(kota_): SBUS_CMD_CANCEL has more tasks to do for cleanup
        # so need more assertions.
        self._test_main_loop_stop(sbus_cmd.SBUS_CMD_CANCEL)


if __name__ == '__main__':
    unittest.main()
