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


class TestCsvStorlet(StorletJavaFunctionalTest):
    def setUp(self):
        self.storlet_log = 'csvstorlet-1.0.log'
        self.additional_headers = {}
        main_class = 'org.openstack.storlet.csv.CSVStorlet'
        super(TestCsvStorlet, self).setUp('CsvStorlet',
                                          'csvstorlet-1.0.jar',
                                          main_class,
                                          'meter-1MB.csv')

    def invoke_storlet(self, start, end,
                       first_partition, max_record_line,
                       columns_selection,
                       where_clause):
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
        headers['X-Storlet-Parameter-5'] = '%s:%s' % ('selected_columns',
                                                      columns_selection)
        headers['X-Storlet-Parameter-6'] = '%s:%s' % ('where_clause',
                                                      where_clause)
        _, content = c.get_object(
            self.url, self.token, self.container, self.storlet_file,
            response_dict=dict(), headers=headers)
        return content

    def _test_filter(self):
        content = self.invoke_storlet(120, 1024,
                                      'false', 512,
                                      '4,6', '')
        for line in content.split('\n'):
            if line:
                self.assertEqual(2, len(line.split(',')))

    def _test_prune(self):
        content = self.invoke_storlet(120, 1024,
                                      'false', 512,
                                      '',
                                      'EqualTo(6,ESP)')
        for line in content.split('\n'):
            if line:
                val = line.split(',')[6]
                self.assertEqual('ESP', val)

    def _test_prune_filter(self):
        content = self.invoke_storlet(120, 1024,
                                      'false', 512,
                                      '4,6',
                                      'EqualTo(6,ESP)')
        for line in content.split('\n'):
            if line:
                val = line.split(',')[1]
                self.assertEqual('ESP', val)

    def _prune_filter_scan_with_count(self, start, stop,
                                      first, max_len,
                                      columns, where):
        content = self.invoke_storlet(start, stop,
                                      first, max_len,
                                      columns, where)
        count = 0
        for line in content.split('\n'):
            if line:
                self.assertEqual('FRA', line.split(',')[1])
                count = count + 1
        return count

    def test_complete_file(self):
        max_len = 512
        c1 = self._prune_filter_scan_with_count(58, 349557,
                                                'true', max_len,
                                                '4,6', 'EqualTo(6,FRA)')
        c2 = self._prune_filter_scan_with_count(349558, 699057,
                                                'false', max_len,
                                                '4,6', 'EqualTo(6,FRA)')
        c3 = self._prune_filter_scan_with_count(699058, 1048558,
                                                'false', max_len,
                                                '4,6', 'EqualTo(6,FRA)')
        self.assertEqual(1070, c1 + c2 + c3)


class TestCsvStorletOnProxy(TestCsvStorlet):
    def setUp(self):
        super(TestCsvStorletOnProxy, self).setUp()
        self.additional_headers = {'X-Storlet-Run-On-Proxy': ''}


if __name__ == '__main__':
    unittest.main()
