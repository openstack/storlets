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

from six.moves import configparser


class ClusterConfig(object):

    def __init__(self, config_path):
        config = configparser.ConfigParser()
        config.read(config_path)
        options = config.options('general')
        self.conf = {}
        for option in options:
            self.conf[option] = config.get('general', option)
        self._auth_version = '3'

    # TODO(eran) get rid of returning raw conf
    def get_conf(self):
        return self.conf

    @property
    def domain_name(self):
        return self.conf['keystone_default_domain']

    @property
    def auth_uri(self):
        return self.conf['keystone_public_url']

    @property
    def project_name(self):
        return self.conf['storlets_default_project_name']

    @property
    def admin_user(self):
        return self.conf['storlets_default_project_user_name']

    @property
    def admin_password(self):
        return self.conf['storlets_default_project_user_password']

    @property
    def member_user(self):
        return self.conf['storlets_default_project_member_user']

    @property
    def member_password(self):
        return self.conf['storlets_default_project_member_password']

    @property
    def region(self):
        return self.conf.get('region', '')

    # TODO(eranr) move to cluster_config
    @property
    def auth_version(self):
        return self._auth_version
