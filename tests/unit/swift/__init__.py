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
import sys
import traceback


class FakeLogger(object):
    def __init__(self, *args, **kwargs):
        pass

    def _print_log(self, level, msg):
        print('%s: %s' % (level, msg))

    def debug(self, msg):
        self._print_log('DEBUG', msg)

    def info(self, msg):
        self._print_log('INFO', msg)

    def warning(self, msg):
        self._print_log('WARN', msg)

    warn = warning

    def error(self, msg):
        self._print_log('ERROR', msg)

    def exception(self, msg):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        exc_msg = traceback.format_exception(exc_type, exc_value,
                                             exc_traceback)
        new_msg = '%s: %s' % (msg, exc_msg)
        self._print_log('EXCEPTION', new_msg)
