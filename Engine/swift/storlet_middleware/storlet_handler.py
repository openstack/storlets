'''-------------------------------------------------------------------------
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
-------------------------------------------------------------------------'''

'''
Created on Feb 18, 2014

@author: Gil Vernik
'''

from storlet_common import StorletTimeout,StorletException

from swift.common.utils import get_logger, register_swift_info, is_success, config_true_value
from swift.common.swob import Request, Response, wsgify, \
                              HTTPBadRequest, HTTPUnauthorized, \
                              HTTPInternalServerError
from swift.proxy.controllers.base import get_account_info
from swift.common.exceptions import ConnectionTimeout
from eventlet import Timeout

import select
import ConfigParser
import os
import sys

class IterLike(object):
    def __init__(self, obj_data, timeout, sprotocol=None):
        self.closed = False
        self.obj_data = obj_data
        self.timeout = timeout
        self.sprotocol = sprotocol

    def __iter__(self):
        return self
            
    def read_with_timeout(self, size):
        timeout = Timeout(self.timeout)
        try:
            chunk = os.read(self.obj_data, size)
        except Timeout as t:
            if t is timeout:
                if self.sprotocol:
                    self.sprotocol._cancel()
                self.close()
                raise t
        except Exception as e:
            self.close()
            raise e
        finally:
            timeout.cancel()

        return chunk
        
    def next(self, size = 1024):
        chunk = None
        r, w, e = select.select([ self.obj_data ], [], [ ], self.timeout)
        if len(r) == 0:
            self.close()
        if self.obj_data in r:
            chunk = self.read_with_timeout(size)
            if chunk == '':
                raise StopIteration('Stopped iterator ex')
            else:
                return chunk
        raise StopIteration('Stopped iterator ex')
             
    def read(self, size=1024):
        return self.next(size)
        
    def readline(self, size=-1):
        return ''
    def readlines(self, sizehint=-1):
        pass;

    def close(self):
        if self.closed == True:
            return
        self.closed = True
        os.close(self.obj_data)
        
    def __del__(self):
        self.close()

class StorletHandlerMiddleware(object):
    
    def __init__(self, app, conf, storlet_conf):
        self.app = app
        self.logger = get_logger(conf, log_route='storlet_handler')
        self.stimeout = int(storlet_conf.get('storlet_timeout'))
        self.storlet_containers = [ storlet_conf.get('storlet_container'),
                                   storlet_conf.get('storlet_dependency')]
        self.execution_server = storlet_conf.get('execution_server')
        self.gateway_module = storlet_conf['gateway_module']
        self.proxy_only_storlet_execution = storlet_conf['storlet_execute_on_proxy_only']
        self.gateway_conf = storlet_conf

        
    @wsgify
    def __call__(self, req):
        try:
            if self.execution_server == 'proxy':
                version, account, container, obj = req.split_path(
                    2, 4, rest_with_last=True)
            else:
                device, partition, account, container, obj = \
                    req.split_path(5, 5, rest_with_last=True)
                version = '0'
        except ValueError as e:
            StorletException.handle(self.logger, e)
            
        self.logger.debug('storlet_handler call in %s: with %s/%s/%s' %
                            (self.execution_server,
                             account,
                             container,
                             obj))

        storlet_execution = False
        if 'X-Run-Storlet' in req.headers:
            storlet_execution = True
        if (storlet_execution == True and account and container and obj) or \
            (container in self.storlet_containers and obj):
                gateway  = self.gateway_module(self.gateway_conf,
                                self.logger, self.app, version, account,
                                container, obj)
        else:
            return req.get_response(self.app) 

        try:                
            if self.execution_server == 'object' and storlet_execution:
                if req.method == 'GET':
                    self.logger.info('GET. Run storlet')
                    orig_resp = req.get_response(self.app)

                    if not is_success(orig_resp.status_int):
                        return orig_resp

                    if self._is_range_request(req) == True or \
                        self._is_slo_get_request(req, orig_resp, account, \
                                               container, obj) or \
                        self.proxy_only_storlet_execution == True:
                        # For SLOs, and proxy only mode
                        # Storlet are executed on the proxy 
                        # Therefore we return the object part without
                        # Storlet invocation:
                        self.logger.info(
                            'storlet_handler: invocation over %s/%s/%s %s' %
                            (account, container, obj,
                            'to be executed on proxy'))
                        return orig_resp
                    else: 
                        # We apply here the Storlet:
                        self.logger.info(
                            'storlet_handler: invocation over %s/%s/%s %s' %
                            (account, container, obj,
                            'to be executed locally'))
                        old_env = req.environ.copy()
                        orig_req = Request.blank(old_env['PATH_INFO'], old_env)
                        (out_md, stream, sprotocol) = gateway.gatewayObjectGetFlow(req,
                                                                        container,
                                                                        obj,
                                                                        orig_resp)
                        if 'Content-Length' in orig_resp.headers:
                            orig_resp.headers.pop('Content-Length')
                        if 'Transfer-Encoding' in orig_resp.headers:
                            orig_resp.headers.pop('Transfer-Encoding')
                      
                        return  Response(
                            app_iter=IterLike(stream, self.stimeout, sprotocol),
                            headers = orig_resp.headers,
                            request=orig_req, 
                            conditional_response=True)

            elif (self.execution_server == 'proxy'):
                if (storlet_execution or container in self.storlet_containers):
                    account_meta = get_account_info(req.environ,
                                                    self.app)['meta']
                    storlets_enabled = account_meta.get('storlet-enabled',
                                                        'False')
                    if storlets_enabled == 'False':
                        self.logger.info('Account disabled for storlets')
                        return HTTPBadRequest('Account disabled for storlets')

                if req.method == 'GET' and storlet_execution:
                    if not gateway.authorizeStorletExecution(req):
                        return HTTPUnauthorized('Storlet: no permission')

                    # The get request may be a SLO object GET request.
                    # Simplest solution would be to invoke a HEAD 
                    # for every GET request to test if we are in SLO case.
                    # In order to save the HEAD overhead we implemented
                    # a slightly more involved flow:
                    # At proxy side, we augment request with Storlet stuff
                    # and let the request flow.
                    # At object side, we invoke the plain (non Storlet)
                    # request and test if we are in SLO case.
                    # and invoke Storlet only if non SLO case.
                    # Back at proxy side, we test if test received 
                    # full object to detect if we are in SLO case, 
                    # and invoke Storlet only if in SLO case.
                    gateway.augmentStorletRequest(req)
                    original_resp = req.get_response(self.app)

                    if self._is_range_request(req) == True or \
                        self._is_slo_get_request(req, original_resp, account, \
                                               container, obj) or \
                        self.proxy_only_storlet_execution == True:
                        # SLO / proxy only  case: 
                        # storlet to be invoked now at proxy side:
                        (out_md, stream, sprotocol) = gateway.gatewayProxyGETFlow(req,
                                                                       container,
                                                                       obj,
                                                                       original_resp)

                        #  adapted from non SLO GET flow
                        if is_success(original_resp.status_int):
                            old_env = req.environ.copy()
                            orig_req = Request.blank(old_env['PATH_INFO'], old_env)
                            resp_headers = original_resp.headers
                    
                            resp_headers['Content-Length'] = None

                            iter = IterLike(stream, self.stimeout, sprotocol)
                            return Response(
                                    app_iter=iter,
                                    headers=resp_headers,
                                    request=orig_req,
                                    conditional_response=True)
                        return original_resp

                    else:
                        # Non proxy GET case: Storlet was already invoked at object side
                        if 'Transfer-Encoding' in original_resp.headers:
                            original_resp.headers.pop('Transfer-Encoding')
                    
                        if is_success(original_resp.status_int):
                            old_env = req.environ.copy()
                            orig_req = Request.blank(old_env['PATH_INFO'], old_env)
                            resp_headers = original_resp.headers
                    
                            resp_headers['Content-Length'] = None
                            return Response(
                                    app_iter=original_resp.app_iter,
                                    headers=resp_headers,
                                    request=orig_req,
                                    conditional_response=True)
                        return original_resp

                elif req.method == 'PUT':
                    if (container in self.storlet_containers):
                        ret = gateway.validateStorletUpload(req)
                        if ret:
                            return HTTPBadRequest(body = ret)
                    else:
                        if not gateway.authorizeStorletExecution(req):
                            return HTTPUnauthorized('Storlet: no permissions')
                    if storlet_execution:
                        gateway.augmentStorletRequest(req)
                        (out_md, stream, sprotocol) = gateway.gatewayProxyPutFlow(req,
                                                                       container,
                                                                       obj)
                        req.environ['wsgi.input'] = IterLike(stream,
                                                             self.stimeout, sprotocol)
                        if 'CONTENT_LENGTH' in req.environ:
                            req.environ.pop('CONTENT_LENGTH')
                        req.headers['Transfer-Encoding'] = 'chunked'
                        return req.get_response(self.app)

        except (StorletTimeout, ConnectionTimeout, Timeout) as e:
            StorletException.handle(self.logger, e) 
            return HTTPInternalServerError(body='Storlet execution timed out')
        except Exception as e:
            StorletException.handle(self.logger, e)
            return HTTPInternalServerError(body='Storlet execution failed')

        return req.get_response(self.app)

    '''
       Determines whether the request is a byte-range request
       args:
       req:       the request
    '''
    def _is_range_request(self, req):
        if 'Range' in req.headers:
            return True
        return False

    '''
       Determines from a GET request and its  associated response 
       if the object is a SLO 
       args:
       req:       the request
       resp:      the response
       account:   the account as extracted from req
       container: the response  as extracted from req
       obj:       the response  as extracted from req
    '''
    def _is_slo_get_request(self, req, resp, account, container, obj):
        if req.method != 'GET':
            return False 
        if req.params.get('multipart-manifest') == 'get':
            return False

        self.logger.info( 'Verify if {0}/{1}/{2} is an SLO assembly object'.format(account,container, obj))

        if resp.status_int < 300 and resp.status_int >= 200 :
            for key in resp.headers:
                if (key.lower() == 'x-static-large-object' and
                    config_true_value(resp.headers[key])):
                    self.logger.info( '{0}/{1}/{2} is indeed an SLO assembly object'.format(account,container, obj))
                    return True
            self.logger.info( '{0}/{1}/{2} is NOT an SLO assembly object'.format(account,container, obj))
            return False
        self.logger.error( 'Failed to check if {0}/{1}/{2} is an SLO assembly object. Got status {3}'.format(account,container, obj,resp.status))
        raise Exception('Failed to check if {0}/{1}/{2} is an SLO assembly object. Got status {3}'.format(account,container, obj,resp.status))

def filter_factory(global_conf, **local_conf):

    conf = global_conf.copy()
    conf.update(local_conf)
    storlet_conf = dict()
    storlet_conf['storlet_timeout'] = conf.get('storlet_timeout',40)
    storlet_conf['storlet_container'] = conf.get('storlet_container','storlet')
    storlet_conf['storlet_dependency'] = conf.get('storlet_dependency',
                                                  'dependency')
    storlet_conf['execution_server'] = conf.get('execution_server', '')
    storlet_conf['storlet_execute_on_proxy_only'] = config_true_value(conf.get('storlet_execute_on_proxy_only', 'false'))
    storlet_conf['gateway_conf'] = {}

    module_name = conf.get('storlet_gateway_module','')
    mo = module_name[:module_name.rfind(':')]
    cl = module_name[module_name.rfind(':') + 1:]
    module = __import__(mo, fromlist=[cl])
    the_class = getattr(module, cl)

    configParser = ConfigParser.RawConfigParser()
    configParser.read(conf.get('storlet_gateway_conf',
                               '/etc/swift/storlet_stub_gateway.conf'))

    additional_items = configParser.items("DEFAULT")
    for key, val in additional_items:
        storlet_conf[key]= val
        
    swift_info = {}
    storlet_conf["gateway_module"] = the_class
    register_swift_info('storlet_handler', False, **swift_info)

    def storlet_handler_filter(app):
        return StorletHandlerMiddleware(app, conf, storlet_conf)
    return storlet_handler_filter

