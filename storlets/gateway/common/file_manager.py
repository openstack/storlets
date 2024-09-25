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
import abc


class FileManager(object, metaclass=abc.ABCMeta):
    """
    This class is used to load/save files required for storlet execution
    from/into the storage which also stores data to be processed
    """

    def __init__(self):
        pass

    @abc.abstractmethod
    def get_storlet(self, name):
        """
        Load storlet file content

        :param name: storlet file name
        """
        pass

    @abc.abstractmethod
    def get_dependency(self, name):
        """
        Load dependency file content

        :param name: dependency file name
        """
        pass

    @abc.abstractmethod
    def put_log(self, name, fobj):
        """
        Save storlet log file to storage

        :param name: log file name
        :param data_iter: File Object
        """
        pass
