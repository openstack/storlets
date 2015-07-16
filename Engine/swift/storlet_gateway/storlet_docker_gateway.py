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
Created on Mar 24, 2015

@author: Yosef Moatti
'''

import os
import sys
import shutil

from swift.common.internal_client import InternalClient as ic
from swift.common.swob import Request
from storlet_runtime import RunTimeSandbox, RunTimePaths
from storlet_runtime import StorletInvocationGETProtocol,\
    StorletInvocationPUTProtocol, StorletInvocationSLOProtocol
from swift.common.utils import config_true_value
from storlet_middleware.storlet_common import StorletGatewayBase

'''---------------------------------------------------------------------------
The Storlet Gateway API
The API is made of:
(1) The classes StorletGETRequest, StorletPUTRequest. These encapsulate
    what goes in and comes out of the gateway. Both share a mutual parent:
    DockerStorletRequest

(2) The StorletGateway is the Docker flavor of the StorletGateway API:
    validateStorletUpload
    authorizeStorletExecution
    augmentStorletRequest
    gatewayProxyPutFlow
    gatewayProxyGetFlow
(3) parse_gateway_conf parses the docker gateway specific configuration. While
    it is part of the API, it is implemented as a static method as the parsing
    of the configuration takes place before the StorletGateway is instantiated
---------------------------------------------------------------------------'''


class DockerStorletRequest():
    '''
    The StorletRequest class represents a request to be processed by the
    storlet the request is derived from the Swift request and
    essentially consists of:
    1. A data stream to be processed
    2. Metadata identifying the stream
    '''
    def user_metadata(self, headers):
        metadata = {}
        for key in headers:
            if (key.startswith('X-Storlet') or
                    key.startswith('X-Object-Meta-Storlet')):
                    pass
            elif (key.startswith('X-Object-Meta-') or
                  key.startswith('X-Object-Meta-'.lower())):
                    short_key = key[len('X-Object-Meta-'):]
                    metadata[short_key] = headers[key]
        return metadata

    def _getInitialRequest(self):
        return self.request

    def __init__(self, account, request, params):
        self.generate_log = request.headers.get('X-Storlet-Generate-Log',
                                                False)
        self.storlet_id = request.headers.get('X-Object-Meta-Storlet-Main')
        self.user_metadata = self.user_metadata(request.headers)
        self.params = params
        self.account = account
        self.request = request
        pass


class StorletGETRequest(DockerStorletRequest):
    def __init__(self, account, orig_resp, params):
        DockerStorletRequest.__init__(self, account, orig_resp, params)
        self.stream = orig_resp.app_iter._fp.fileno()


class StorletPUTRequest(DockerStorletRequest):
    def __init__(self, account, request):
        DockerStorletRequest.__init__(self, account, request, request.params)
        self.stream = request.environ['wsgi.input'].read
        return


class StorletSLORequest(DockerStorletRequest):
    def __init__(self, account, orig_resp, params):
        DockerStorletRequest.__init__(self, account, orig_resp, params)
        self.stream = orig_resp.app_iter
        return


class StorletGatewayDocker(StorletGatewayBase):

    def __init__(self, sconf, logger, app, version, account, container,
                 obj):
        self.logger = logger
        self.app = app
        self.version = version
        self.account = account
        self.container = container
        self.obj = obj
        self.sconf = sconf
        self.storlet_metadata = None
        self.storlet_timeout = int(self.sconf['storlet_timeout'])
        self.paths = RunTimePaths(account, sconf)

    def validateStorletUpload(self, req):

        if (self.container == self.sconf['storlet_container']):
            if (self.obj.find('-') < 0 or self.obj.find('.') < 0):
                return 'Storlet name is incorrect'

        ret = self._validate_mandatory_headers(req)
        if ret:
            return ret
        return False

    def authorizeStorletExecution(self, req):
        res, headers = self.verify_access(req.environ,
                                          self.version,
                                          self.account,
                                          self.sconf['storlet_container'],
                                          req.headers['X-Run-Storlet'])
        if not res:
            return False

        # keep the storlets headers for later use.
        self.storlet_metadata = headers
        return True

    def augmentStorletRequest(self, req):
        if self.storlet_metadata:
            self._fix_request_headers(req)

    def gatewayProxyPutFlow(self, orig_req, container, obj):
        sreq = StorletPUTRequest(self.account, orig_req)
        req = sreq._getInitialRequest()
        self.idata = self._get_storlet_invocation_data(req)
        run_time_sbox = RunTimeSandbox(self.account, self.sconf, self.logger)
        docker_updated = self.update_docker_container_from_cache()
        run_time_sbox.activate_storlet_daemon(self.idata,
                                              docker_updated)
        self._add_system_params(req.params)
        # Clean all Storlet stuff from the request headers
        # we do not need them anymore, and they
        # may interfere with the rest of the execution.
        self._clean_storlet_stuff_from_request(req.headers)
        req.headers.pop('X-Run-Storlet')

        slog_path = self.\
            paths.slog_path(self.idata['storlet_main_class'])
        storlet_pipe_path = self.\
            paths.host_storlet_pipe(self.idata['storlet_main_class'])

        sprotocol = StorletInvocationPUTProtocol(sreq,
                                                 storlet_pipe_path,
                                                 slog_path,
                                                 self.storlet_timeout)
        out_md, self.data_read_fd = sprotocol.communicate()

        self._set_metadata_in_headers(req.headers, out_md)
        self._upload_storlet_logs(slog_path)

        return out_md, self.data_read_fd, sprotocol

    def gatewayProxyGETFlow(self, req, container, obj, orig_resp):
        # Flow for running the GET computation on the proxy
        sreq = StorletSLORequest(self.account, orig_resp, req.params)

        self.idata = self._get_storlet_invocation_data(req)
        run_time_sbox = RunTimeSandbox(self.account, self.sconf, self.logger)
        docker_updated = self.update_docker_container_from_cache()
        run_time_sbox.activate_storlet_daemon(self.idata,
                                              docker_updated)
        self._add_system_params(req.params)

        slog_path = self.\
            paths.slog_path(self.idata['storlet_main_class'])
        storlet_pipe_path = self.\
            paths.host_storlet_pipe(self.idata['storlet_main_class'])

        sprotocol = StorletInvocationSLOProtocol(sreq,
                                                 storlet_pipe_path,
                                                 slog_path,
                                                 self.storlet_timeout)
        out_md, self.data_read_fd = sprotocol.communicate()

        self._set_metadata_in_headers(orig_resp.headers, out_md)
        self._upload_storlet_logs(slog_path)

        return out_md, self.data_read_fd, sprotocol

    def gatewayObjectGetFlow(self, req, container, obj, orig_resp):
        sreq = StorletGETRequest(self.account, orig_resp, req.params)

        self.idata = self._get_storlet_invocation_data(req)
        run_time_sbox = RunTimeSandbox(self.account, self.sconf, self.logger)
        docker_updated = self.update_docker_container_from_cache()
        run_time_sbox.activate_storlet_daemon(self.idata,
                                              docker_updated)
        self._add_system_params(req.params)

        slog_path = self.\
            paths.slog_path(self.idata['storlet_main_class'])
        storlet_pipe_path = self.paths.\
            host_storlet_pipe(self.idata['storlet_main_class'])

        sprotocol = StorletInvocationGETProtocol(sreq, storlet_pipe_path,
                                                 slog_path,
                                                 self.storlet_timeout)
        out_md, self.data_read_fd = sprotocol.communicate()

        orig_resp = sreq._getInitialRequest()
        self._set_metadata_in_headers(orig_resp.headers, out_md)
        self._upload_storlet_logs(slog_path)

        return out_md, self.data_read_fd, sprotocol

    def verify_access(self, env, version, account, container, object):
        self.logger.info('Verify access to {0}/{1}/{2}'.format(account,
                                                               container,
                                                               object))
        new_env = dict(env)
        if 'HTTP_TRANSFER_ENCODING' in new_env.keys():
            del new_env['HTTP_TRANSFER_ENCODING']
        new_env['REQUEST_METHOD'] = 'HEAD'
        new_env['swift.source'] = 'SE'
        new_env['PATH_INFO'] = os.path.join('/' + version, account,
                                            container, object)
        new_env['RAW_PATH_INFO'] = os.path.join('/' + version, account,
                                                container, object)
        storlet_req = Request.blank(new_env['PATH_INFO'], new_env)

        resp = storlet_req.get_response(self.app)
        if resp.status_int < 300 and resp.status_int >= 200:
            return True, resp.headers
        return False, []

    def _validate_mandatory_headers(self, req):
        mandatory_md = None
        if self.container in [self.sconf['storlet_container']]:
            self.logger.info('PUT method for storlet dependency. Sanity check')
            mandatory_md = ['X-Object-Meta-Storlet-Language',
                            'X-Object-Meta-Storlet-Interface-Version',
                            'X-Object-Meta-Storlet-Dependency',
                            'X-Object-Meta-Storlet-Object-Metadata',
                            'X-Object-Meta-Storlet-Main']
        elif self.container in [self.sconf['storlet_dependency']]:
            self.logger.info('PUT method for storlet container.  Sanity check')
            mandatory_md = ['X-Object-Meta-Storlet-Dependency-Version']

        if mandatory_md is not None:
            for md in mandatory_md:
                if md not in req.headers:
                    self.logger.info('Mandatory header ' +
                                     'is missing: {0}'.format(md))
                    return 'Mandatory header is missing: {0}'.format(md)
        return None

    def _fix_request_headers(self, req):
        # add to request the storlet metadata to be used in case the request
        # is forwarded to the data node (GET case)
        for key, val in self.storlet_metadata.iteritems():
            if key.startswith('X-Object-Meta-Storlet'):
                req.headers[key] = val
            elif key in ['X-Timestamp', 'Content-Length']:
                req.headers['X-Storlet-' + key] = val

    def _add_system_params(self, params):
        '''
        Adds Storlet engine specific parameters to the invocation
        currently, this consists only of the execution path of the
        Storlet within the Docker container.
        '''
        params['storlet_execution_path'] = self.\
            paths.sbox_storlet_exec(self.idata['storlet_main_class'])

    def _clean_storlet_stuff_from_request(self, headers):
        for key in headers:
            if (key.startswith('X-Storlet') or
                    key.startswith('X-Object-Meta-Storlet')):
                    del headers[key]
        return headers

    def _get_storlet_invocation_data(self, req):
        data = dict()
        data['storlet_name'] = req.headers.get('X-Run-Storlet')
        data['generate_log'] = req.headers.get('X-Storlet-Generate-Log', False)
        data['storlet_original_timestamp'] = req.headers.\
            get('X-Storlet-X-Timestamp')
        data['storlet_original_size'] = req.headers.\
            get('X-Storlet-Content-Length')
        data['storlet_md'] = {'storlet_original_timestamp':
                              data['storlet_original_timestamp'],
                              'storlet_original_size':
                              data['storlet_original_size']}
        data['storlet_main_class'] = req.headers.\
            get('X-Object-Meta-Storlet-Main')

        scope = self.account
        data['scope'] = scope
        if data['scope'].rfind(':') > 0:
            data['scope'] = data['scope'][:data['scope'].rfind(':')]

        data['storlet_dependency'] = req.headers.\
            get('X-Object-Meta-Storlet-Dependency')
        data['request_params'] = req.params
        return data

    def _set_metadata_in_headers(self, headers, md):
        if md:
            for key, val in md.iteritems():
                headers['X-Object-Meta-%s' % key] = val

    def _upload_storlet_logs(self, slog_path):
        if (config_true_value(self.idata['generate_log'])):
            logfile = open(slog_path, 'r')
            client = ic('/etc/swift/storlet-proxy-server.conf', 'SA', 1)
            try:
                headers = dict()
                headers['CONTENT_TYPE'] = 'text/html'
                log_obj_name = '%s.log' %\
                    self.idata['storlet_name'][:self.idata['storlet_name'].
                                               find('-')]
                client.upload_object(logfile, self.account,
                                     self.sconf['storlet_logcontainer'],
                                     log_obj_name, headers)
            except Exception as e:
                raise e

    def bring_from_cache(self, obj_name, is_storlet):
        '''
        Auxiliary function that:
        (1) Brings from Swift obj_name, whether this is a
            storlet or a storlet dependency.
        (2) Copies from local cache into the Docker conrainer
        If this is a Storlet then also validates that the cache is updated
        with most recent copy of the Storlet compared to the copy residing in
        Swift.
        Retunrs wheather the Docker container was updated with obj_name
        '''
        # Determine the cache we are to work with
        # e.g. dependency or storlet
        if not is_storlet:
            cache_dir = self.paths.get_host_dependency_cache_dir()
            swift_source_container = self.paths.storlet_dependency
        else:
            cache_dir = self.paths.get_host_storlet_cache_dir()
            swift_source_container = self.paths.storlet_container

        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, 0755)

        # cache_target_path is the actual object we need to deal with
        # e.g. a concrete storlet or dependency we need to bring/update
        cache_target_path = os.path.join(cache_dir, obj_name)

        # Determine if we need to update the cache for cache_target_path
        # We default for no
        update_cache = False

        # If it does not exist in cache, we obviously need to bring
        if not os.path.isfile(cache_target_path):
            update_cache = True
        elif is_storlet:
            # The cache_target_path exists, we test if it is up-to-date
            # with the metadata we got.
            # We mention that this is currenlty applicable for storlets
            # only, and not for dependencies.
            # This will change when we will head dependencies as well
            storlet_md = self.idata['storlet_md']
            fstat = os.stat(cache_target_path)
            storlet_or_size = long(storlet_md['storlet_original_size'])
            storlet_or_time = float(storlet_md['storlet_original_timestamp'])
            b_storlet_size_changed = fstat.st_size != storlet_or_size
            b_storlet_file_updated = float(fstat.st_mtime) < storlet_or_time
            if b_storlet_size_changed or b_storlet_file_updated:
                update_cache = True

        expected_perm = ''
        if update_cache:
            # If the cache needs to be updated, then get on with it
            # bring the object from Swift using ic
            client = ic('/etc/swift/storlet-proxy-server.conf', 'SA', 1)
            path = client.make_path(self.account, swift_source_container,
                                    obj_name)
            self.logger.debug('Invoking ic on path %s' % path)
            resp = client.make_request('GET', path, {'PATH_INFO': path}, [200])
            fn = open(cache_target_path, 'w')
            fn.write(resp.body)
            fn.close()

            if not is_storlet:
                expected_perm = resp.headers.\
                    get('X-Object-Meta-Storlet-Dependency-Permissions', '')
                if expected_perm != '':
                    os.chmod(cache_target_path, int(expected_perm, 8))

        # The node's local cache is now updated.
        # We now verify if we need to update the
        # Docker container itself.
        # The Docker container needs to be updated if:
        # 1. The Docker container does not hold a copy of the object
        # 2. The Docker container holds an older version of the object
        update_docker = False
        docker_storlet_path = self.paths.\
            host_storlet(self.idata['storlet_main_class'])
        docker_target_path = os.path.join(docker_storlet_path, obj_name)

        if not os.path.exists(docker_storlet_path):
            os.makedirs(docker_storlet_path, 0755)
            update_docker = True
        elif not os.path.isfile(docker_target_path):
            update_docker = True
        else:
            fstat_cached_object = os.stat(cache_target_path)
            fstat_docker_object = os.stat(docker_target_path)
            b_size_changed = fstat_cached_object.st_size \
                != fstat_docker_object.st_size
            b_time_changed = float(fstat_cached_object.st_mtime) <\
                float(fstat_docker_object.st_mtime)
            if (b_size_changed or b_time_changed):
                update_docker = True

        if update_docker:
            # need to copy from cache to docker
            # copy2 also copies the permissions
            shutil.copy2(cache_target_path, docker_target_path)

        return update_docker

    def update_docker_container_from_cache(self):
        '''
        Iterates over the storlet name and its dependencies appearing
        in the invocation data and make sure they are brought to the
        local cache, and from there to the Docker container.
        Uses the bring_from_cache auxiliary function.
        Returns True if the Docker container was updated
        '''
        # where at the host side, reside the storlet containers
        storlet_path = self.paths.host_storlet_prefix()
        if not os.path.exists(storlet_path):
            os.makedirs(storlet_path, 0755)

        # Iterate over storlet and dependencies, and make sure
        # they are updated within the Docker container.
        # return True if any of them wea actually
        # updated within the Docker container
        docker_updated = False

        updated = self.bring_from_cache(self.idata['storlet_name'],
                                        True)
        docker_updated = docker_updated or updated

        if self.idata['storlet_dependency']:
            for dep in self.idata['storlet_dependency'].split(','):
                updated = self.bring_from_cache(dep, False)
                docker_updated = docker_updated or updated

        return docker_updated


def validate_conf(middleware_conf):
    mandatory = ['storlet_logcontainer', 'lxc_root', 'cache_dir',
                 'log_dir', 'script_dir', 'storlets_dir', 'pipes_dir',
                 'docker_repo', 'restart_linux_container_timeout']
    for key in mandatory:
        if key not in mandatory:
            raise Exception("Key {} is missing in configuration".format(key))
