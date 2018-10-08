# Copyright (c) 2010-2016 OpenStack Foundation
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

from swiftclient import client as c
from tests.functional.java import StorletJavaFunctionalTest
import unittest

# Below is the records.txt file we are testing with
# position line content
# 0        header line
# 12       random text 1
# 26       random text 2
# 40       random text 3
# 54       random text 4
# 68       random text 5
# 82       random text 6
# 96       random text 7
# 110      random text 8
# 124      random text 9
# 138      random text 10
# 153      random text 100
# 169      random text 1000
# 186      random text 10000
# 204      ....
records_txt = \
    "header line\n\
random text 1\n\
random text 2\n\
random text 3\n\
random text 4\n\
random text 5\n\
random text 6\n\
random text 7\n\
random text 8\n\
random text 9\n\
random text 10\n\
random text 100\n\
random text 1000\n\
random text 10000\n\
random text 1\n"


class TestPartitionsIdentityStorlet(StorletJavaFunctionalTest):
    def setUp(self):
        self.storlet_log = 'partitionsidentitystorlet-1.0.log'
        self.additional_headers = {}
        main_class = 'org.openstack.storlet.PartitionsIdentityStorlet'
        super(TestPartitionsIdentityStorlet, self).setUp(
            'PartitionsIdentityStorlet',
            'partitionsidentitystorlet-1.0.jar',
            main_class,
            'records.txt')

    def invoke_storlet(self, start, end, first_partition, max_record_line):
        headers = {'X-Run-Storlet': self.storlet_name}
        headers.update(self.additional_headers)
        headers['X-Storlet-Range'] = 'bytes=%d-%d' % (start,
                                                      end + max_record_line)
        headers['X-Storlet-Parameter-1'] = '%s:%s' % ('start', start)
        headers['X-Storlet-Parameter-2'] = '%s:%s' % ('end', end)
        headers['X-Storlet-Parameter-3'] = '%s:%s' % ('max_record_line',
                                                      max_record_line)
        headers['X-Storlet-Parameter-4'] = '%s:%s' % ('first_partition',
                                                      first_partition)
        _, content = c.get_object(
            self.url, self.token, self.container, self.storlet_file,
            response_dict=dict(), headers=headers)
        return content

    # The input file in our case has the following characteristics:
    # It has a header line and actual data starts at byte 13
    # Since the first byte is at location 0, the 13th byte is at location 12
    # The max line is 18 chars (including '\n')
    # Here are the tests we do:
    # 1. First range tests:
    #   - range Starts with 13
    #   - firstLine param is set to True
    #   - use various max_line_len
    #   - use various end bytes
    # 2. Second range tests
    #   - range can start at any location
    #   - firstLine param is set to False
    #   - use various start, end bytes

    def _test_first_range(self, max_record_line):
        # According to the file's content end=82 should give us
        # lines 1-5, plus line 6 as the extra line
        content = self.invoke_storlet(12, 82, 'true', max_record_line)
        # byte 95 is the newline of line 6
        self.assertEqual(content, records_txt[12:95] + '\n')
        # end=83,85,...,94 gets us deeper into the same line,
        # output should be the same:
        # lines 1-5, plus line 6 as the extra line
        for i in range(12):
            content = self.invoke_storlet(12, i + 83, 'true', max_record_line)
            self.assertEqual(content, records_txt[12:95] + '\n')
        # Now that we move one extra character we get a different answer
        content = self.invoke_storlet(12, 95, 'true', max_record_line)
        self.assertNotEqual(content, records_txt[12:95] + '\n')

    def _test_second_range(self, max_record_line):
        # According to the file's content start=82 should give us
        # line 7 as the first line (dropping line 6)
        # end=185 should give us line 13 as well as an extra line
        # and it should skip line 6 being the first line
        content = self.invoke_storlet(82, 185, 'false', max_record_line)
        self.assertEqual(content, records_txt[96:203] + '\n')
        # starting from 83 up to 95 should give the exact result
        for i in range(12):
            content = self.invoke_storlet(i + 83, 185, 'false',
                                          max_record_line)
            self.assertEqual(content, records_txt[96:203] + '\n')
        # ending at any point up to 202 should give the exact result
        for i in range(16):
            content = self.invoke_storlet(82, 186 + i, 'false',
                                          max_record_line)
            self.assertEqual(content, records_txt[96:203] + '\n')
        # now for the combinations of the two:
        for i in range(12):
            for j in range(16):
                content = self.invoke_storlet(83 + i, 186 + j, 'false',
                                              max_record_line)
                self.assertEqual(content, records_txt[96:203] + '\n')

    def test_second_range(self):
        self._test_second_range(80)

    def test_first_range(self):
        for max_record_line in range(5):
            # The maximium line length in this section is 14
            # includuing the new line. and so any max length >=14
            # should be good.
            self._test_first_range(80)


class TestPartitionsIdentityStorletOnProxy(TestPartitionsIdentityStorlet):
    def setUp(self):
        super(TestPartitionsIdentityStorletOnProxy, self).setUp()
        self.additional_headers = {'X-Storlet-Run-On-Proxy': ''}


if __name__ == '__main__':
    unittest.main()
