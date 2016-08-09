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
from storlet_gateway.common.exceptions import StorletGatewayLoadError


def load_gateway(module_name):
    module_name_sp = module_name.split(':')
    if not len(module_name_sp):
        raise StorletGatewayLoadError('Invalid module name: %s' %
                                      module_name)

    try:
        # TODO(takashi): Can we use stevedore to load module?
        module = __import__(module_name_sp[0], fromlist=[module_name_sp[1]])
        return getattr(module, module_name_sp[1])
    except (ImportError, AttributeError) as e:
        raise StorletGatewayLoadError('Failed to load gateway class: %s' %
                                      str(e))
