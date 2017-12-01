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


class MultiInputStorlet(object):
    def __init__(self, logger):
        self.logger = logger

    def __call__(self, in_files, out_files, params):
        """
        The function called for storlet invocation

        :param in_files: a list of StorletInputFile
        :param out_files: a list of StorletOutputFile
        :param params: a dict of request parameters
        """

        metadata = {}
        for input_file in in_files:
            metadata.update(input_file.get_metadata())
        out_files[0].set_metadata(metadata)

        self.logger.debug('Start to return object data')
        for input_file in in_files:
            while True:
                buf = input_file.read(16)
                if not buf:
                    break
                self.logger.debug('Received %d bytes' % len(buf))
                out_files[0].write(buf)
        self.logger.debug('Complete')
        for input_file in in_files:
            input_file.close()
        out_files[0].close()
