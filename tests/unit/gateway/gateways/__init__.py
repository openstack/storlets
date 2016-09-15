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
from six import StringIO


class FakeFileManager(object):
    def __init__(self, storlet, dependency, storlet_perm=None,
                 dependency_perm=None):
        self.storlet = storlet
        self.dependency = dependency
        self.storlet_perm = storlet_perm
        self.dependency_perm = dependency_perm

    def get_storlet(self, name):
        return StringIO(self.storlet), self.storlet_perm

    def get_dependency(self, name):
        return StringIO(self.dependency), self.dependency_perm

    def put_log(self, name, fobj):
        pass
