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

from swift.common.swob import Request
from storlet_middleware.handlers import StorletBaseHandler


class TestStorletBaseHandler(unittest.TestCase):
    def test_init_failed_via_base_handler(self):
        def assert_not_implemented(method, path, headers):
            req = Request.blank(
                path, environ={'REQUEST_METHOD': method},
                headers=headers)
            try:
                StorletBaseHandler(
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


if __name__ == '__main__':
    unittest.main()
