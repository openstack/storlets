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

import random


class MultiInputMIMEStorlet(object):
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
        mime_boundary = "%.64x" % random.randint(0, 16 ** 64)
        metadata['Content-Type'] = \
            'multipart/mixed; boundary=%s' % mime_boundary
        out_files[0].set_metadata(metadata)

        self.logger.debug('Start to return object data')
        while in_files:
            input_file = in_files.pop(0)
            while True:
                buf = input_file.read(16)
                if not buf:
                    break
                self.logger.debug('Received %d bytes' % len(buf))
                out_files[0].write(buf)
            input_file.close()
            if in_files:
                # in_files still have items
                out_files[0].write('\n--%s\n' % mime_boundary)
            else:
                # this is the end of input_files so the boundary should end
                # the content
                out_files[0].write('\n--%s--' % mime_boundary)

        self.logger.debug('Complete')
        out_files[0].close()
