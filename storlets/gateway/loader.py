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
import sys
from stevedore import driver
from storlets.gateway.common.exceptions import StorletGatewayLoadError


def load_gateway(gateway_name):
    """
    Load gateway class for the given name

    :param gateway_name: a name of the gateway class to be loaded
                         you can specify its entry point name or full path
    :returns: a gateway class loaded
    :raises StorletGatewayLoadError: when it fails to load the given gateway
    """

    namespace = 'storlets.gateways'
    try:
        # Try to load gateway class using entry point
        driver_manager = driver.DriverManager(namespace, gateway_name,
                                              invoke_on_load=False)
        return driver_manager.driver
    except RuntimeError:
        # Currently we can not find the entry point, so try again to load
        # using full class path
        mod_str, _sep, class_str = gateway_name.rpartition('.')
        if not mod_str:
            raise StorletGatewayLoadError(
                'Invalid class path is given for gateway class name %s' %
                gateway_name)
        try:
            __import__(mod_str)
            return getattr(sys.modules[mod_str], class_str)
        except (ImportError, AttributeError):
            raise StorletGatewayLoadError('Failed to load gateway %s' %
                                          gateway_name)
