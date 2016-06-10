"""-------------------------------------------------------------------------
Copyright IBM Corp. 2015, 2015 All Rights Reserved
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
Limitations under the License.
-------------------------------------------------------------------------"""

import ConfigParser
from eventlet import Timeout
from swift.common.swob import HTTPException, HTTPInternalServerError, wsgify
from swift.common.utils import config_true_value, get_logger, \
    register_swift_info
from storlet_gateway.common.exceptions import StorletRuntimeException, \
    StorletTimeout
from storlet_middleware.handlers.base import NotStorletRequest
from storlet_middleware.handlers import StorletProxyHandler, \
    StorletObjectHandler


class StorletHandlerMiddleware(object):

    def __init__(self, app, conf, storlet_conf):
        self.app = app
        self.logger = get_logger(conf, log_route='storlet_handler')
        self.stimeout = int(storlet_conf.get('storlet_timeout'))
        self.storlet_containers = [storlet_conf.get('storlet_container'),
                                   storlet_conf.get('storlet_dependency')]
        self.exec_server = storlet_conf.get('execution_server')
        self.handler_class = self._get_handler(self.exec_server)
        self.gateway_module = storlet_conf['gateway_module']
        self.proxy_only_storlet_execution = \
            storlet_conf['storlet_execute_on_proxy_only']
        self.gateway_conf = storlet_conf

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
                req, self.gateway_conf, self.app, self.logger)
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
    storlet_conf = dict()
    storlet_conf['storlet_timeout'] = conf.get('storlet_timeout', 40)
    storlet_conf['storlet_container'] = \
        conf.get('storlet_container', 'storlet')
    storlet_conf['storlet_dependency'] = conf.get('storlet_dependency',
                                                  'dependency')
    storlet_conf['execution_server'] = conf.get('execution_server', '')
    storlet_conf['storlet_execute_on_proxy_only'] = \
        config_true_value(conf.get('storlet_execute_on_proxy_only', 'false'))
    storlet_conf['gateway_conf'] = {}
    storlet_conf['reseller_prefix'] = conf.get('reseller_prefix', 'AUTH')

    module_name = conf.get('storlet_gateway_module', '')
    mo = module_name[:module_name.rfind(':')]
    cl = module_name[module_name.rfind(':') + 1:]
    module = __import__(mo, fromlist=[cl])
    the_class = getattr(module, cl)

    configParser = ConfigParser.RawConfigParser()
    configParser.read(conf.get('storlet_gateway_conf',
                               '/etc/swift/storlet_stub_gateway.conf'))

    additional_items = configParser.items("DEFAULT")
    for key, val in additional_items:
        storlet_conf[key] = val

    # TODO(eranr): Add supported storlets languages and
    #  supported storlet API version
    swift_info = {'storlet_container': storlet_conf['storlet_container'],
                  'storlet_dependency': storlet_conf['storlet_dependency'],
                  'storlet_gateway_class': cl}

    storlet_conf["gateway_module"] = the_class
    register_swift_info('storlet_handler', False, **swift_info)

    def storlet_handler_filter(app):
        return StorletHandlerMiddleware(app, conf, storlet_conf)
    return storlet_handler_filter
