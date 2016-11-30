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

import logging
import unittest
from six import StringIO

from storlets.agent.common.utils import get_logger


class TestLogger(unittest.TestCase):

    def test_get_logger(self):
        sio = StringIO()
        logger = logging.getLogger('CONT #abcdef: test')
        logger.addHandler(logging.StreamHandler(sio))

        # set log level as INFO
        logger = get_logger('test', 'INFO', 'abcdef')
        self.assertEqual(logging.INFO, logger.level)
        # INFO message is recorded with INFO log level
        logger.info('test1')
        self.assertEqual('test1\n', sio.getvalue())
        # DEBUG message is not recorded with INFO log level
        logger.debug('test2')
        self.assertEqual('test1\n', sio.getvalue())

        # set log level as DEBUG
        logger = get_logger('test', 'DEBUG', 'abcdef')
        self.assertEqual(logging.DEBUG, logger.level)
        # DEBUG message is recorded with DEBUG log level
        logger.debug('test3')
        self.assertEqual('test1\ntest3\n', sio.getvalue())

        # If the level parameter is unknown, use ERROR as log level
        logger = get_logger('test', 'foo', 'abcdef')
        self.assertEqual(logging.ERROR, logger.level)


if __name__ == '__main__':
    unittest.main()
