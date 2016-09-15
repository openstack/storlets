# Copyright (c) 2015, 2016 OpenStack Foundation.
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

from six.moves import configparser as ConfigParser
from eventlet import Timeout
from swift.common.swob import HTTPException, HTTPInternalServerError, wsgify
from swift.common.utils import get_logger, register_swift_info
from storlets.gateway.common.exceptions import StorletRuntimeException, \
    StorletTimeout
from storlets.gateway.loader import load_gateway
from storlets.swift_middleware.handlers.base import NotStorletRequest, \
    get_container_names
from storlets.swift_middleware.handlers import StorletProxyHandler, \
    StorletObjectHandler


class StorletHandlerMiddleware(object):

    def __init__(self, app, conf, gateway_conf):
        self.app = app
        self.logger = get_logger(conf, log_route='storlet_handler')
        self.exec_server = conf.get('execution_server')
        self.handler_class = self._get_handler(self.exec_server)
        self.conf = conf
        self.gateway_conf = gateway_conf

    def _get_handler(self, exec_server):
        """
        Generate Handler class based on execution_server parameter

        :param exec_server: Where this storlet_middleware is running.
                            This should value shoud be 'proxy' or 'object'
        :raise ValueError: If exec_server is invalid
        """
        if exec_server == 'proxy':
            return StorletProxyHandler
        elif exec_server == 'object':
            return StorletObjectHandler
        else:
            raise ValueError(
                'configuration error: execution_server must be either proxy'
                ' or object but is %s' % exec_server)

    @wsgify
    def __call__(self, req):
        try:
            request_handler = self.handler_class(
                req, self.conf, self.gateway_conf, self.app, self.logger)
            self.logger.debug('storlet_handler call in %s: with %s/%s/%s' %
                              (self.exec_server, request_handler.account,
                               request_handler.container, request_handler.obj))
        except HTTPException:
            raise
        except NotStorletRequest:
            return req.get_response(self.app)

        try:
            return request_handler.handle_request()

        # TODO(takashi): Consider handling them in lower layers
        except StorletTimeout:
            self.logger.exception('Storlet execution timed out')
            raise HTTPInternalServerError(body='Storlet execution timed out')
        except StorletRuntimeException:
            self.logger.exception('Storlet execution failed')
            raise HTTPInternalServerError(body='Storlet execution failed')
        except Timeout:
            self.logger.exception('Internal request timed out')
            raise HTTPInternalServerError(body='Internal request timed out')
        except HTTPException:
            # TODO(takashi): Shoud we generate this log for all error?
            #                (ex. 404 when the object is not found)
            self.logger.exception('Storlet execution failed')
            raise
        except Exception:
            self.logger.exception('Internal server error')
            raise HTTPInternalServerError(body='Internal server error')


def filter_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)

    module_name = conf.get('storlet_gateway_module', 'stub')
    gateway_class = load_gateway(module_name)
    conf['gateway_module'] = gateway_class

    configParser = ConfigParser.RawConfigParser()
    configParser.read(conf.get('storlet_gateway_conf',
                               '/etc/swift/storlet_stub_gateway.conf'))
    gateway_conf = dict(configParser.items("DEFAULT"))

    # TODO(eranr): Add supported storlets languages and
    #  supported storlet API version
    containers = get_container_names(conf)
    swift_info = {'storlet_container': containers['storlet'],
                  'storlet_dependency': containers['dependency'],
                  'storlet_gateway_class': gateway_class.__name__}
    register_swift_info('storlet_handler', False, **swift_info)

    def storlet_handler_filter(app):
        return StorletHandlerMiddleware(app, conf, gateway_conf)
    return storlet_handler_filter
