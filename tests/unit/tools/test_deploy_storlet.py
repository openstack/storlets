# Copyright (c) 2016 OpenStack Foundation.
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
import mock
from storlets.tools.deploy_storlet import main


class TestDeployStorlet(unittest.TestCase):
    # TODO(kota_): missing test cases like:
    #              - no class found in the jar
    #              - not a class in the list
    #              - fail to open the jar file
    #                (e.g. no such a file or directry)
    def test_deploy_storlet_main_java(self):
        class MockZipFile(mock.MagicMock):
            def infolist(self):
                mock_file = mock.MagicMock()
                mock_file.filename = 'main_class.class'
                return [mock_file]

            def __enter__(self):
                return self

            def __exit__(self, *args, **kwargs):
                pass

        with mock.patch('zipfile.ZipFile', MockZipFile):
            self._test_deploy_storlet_main('java')

    def test_deploy_storlet_main_python(self):
        self._test_deploy_storlet_main('python')

    def _test_deploy_storlet_main(self, lang):
        # TODO(kota_): avoid mock for ClusterConfig and get_auth
        get_auth_func_path = 'storlets.tools.deploy_storlet.get_auth'
        deploy_storlet_path = 'storlets.tools.deploy_storlet.deploy_storlet'
        with mock.patch('storlets.tools.deploy_storlet.ClusterConfig'), \
                mock.patch(deploy_storlet_path) as mock_deploy_storlet, \
                mock.patch(get_auth_func_path) as mock_auth:

            mock_auth.return_value = ('url', 'token')
            stdins = [
                lang, 'storlet_file_path', 'main_class', ''
            ]

            class MockStdin(object):
                def readline(self):
                    return stdins.pop(0)

            with mock.patch('sys.stdin', MockStdin()):
                main(['dummy_config_path'])

        # sanity
        self.assertEqual(1, mock_deploy_storlet.call_count)
        self.assertEqual(
            mock.call('url', 'token', storlet='storlet_file_path',
                      storlet_main_class='main_class', dependencies=[],
                      language=lang.title()),
            mock_deploy_storlet.call_args)


if __name__ == '__main__':
    unittest.main()
