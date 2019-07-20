# Copyright IBM Corp. 2015, 2015 All Rights Reserved
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

import os
from contextlib import contextmanager
from storlets.gateway.common.exceptions import StorletLoggerError


class StorletLogger(object):
    def __init__(self, path):
        self.log_path = path
        self._file = None

    def open(self):
        if self._file is not None:
            raise StorletLoggerError('StorletLogger is already open')

        try:
            log_dir_path = os.path.dirname(self.log_path)
            if not os.path.exists(log_dir_path):
                os.makedirs(log_dir_path)

            self._file = open(self.log_path, 'a')
        except Exception:
            raise

    def getfd(self):
        if self._file is None:
            # TODO(kota_): Is it safe to return None?
            return None
        return self._file.fileno()

    def getsize(self):
        statinfo = os.stat(self.log_path)
        return statinfo.st_size

    def close(self):
        if self._file is None:
            raise StorletLoggerError('StorletLogger is not open')

        try:
            self._file.close()
        except Exception:
            raise
        else:
            self._file = None

    @contextmanager
    def activate(self):
        self.open()
        try:
            yield
        finally:
            self.close()
