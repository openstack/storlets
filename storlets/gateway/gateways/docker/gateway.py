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

import os
import shutil

from storlets.agent.common.utils import DEFAULT_PY2, DEFAULT_PY3
from storlets.gateway.common.stob import StorletRequest
from storlets.gateway.gateways.base import StorletGatewayBase
from storlets.gateway.gateways.docker.runtime import RunTimePaths, \
    RunTimeSandbox, StorletInvocationProtocol


CONDITIONAL_KEYS = ['IF_MATCH', 'IF_NONE_MATCH', 'IF_MODIFIED_SINCE',
                    'IF_UNMODIFIED_SINCE']

"""---------------------------------------------------------------------------
The Storlet Gateway API
The API is made of:
(1) The class DockerStorletRequest. This encapsulates what goes in and comes
    out of the gateway
(2) The StorletGateway is the Docker flavor of the StorletGateway API:
    validate_storlet_registration
    validate_dependency_registration
    invocation_flow
---------------------------------------------------------------------------"""


class DockerStorletRequest(StorletRequest):
    """
    The DockerStorletRequest class represents a request to be processed by the
    storlet the request is derived from the Swift request and
    essentially consists of:
    1. A data stream to be processed
    2. Metadata identifying the stream
    """

    # TODO(takashi): Some of following parameters should be defined common
    #                parameters for StorletRequest
    required_options = ['storlet_main', 'storlet_language', 'file_manager']

    def __init__(self, storlet_id, params, user_metadata, data_iter=None,
                 data_fd=None, options=None):
        """
        :param storlet_id: storlet id
        :param params: execution parameters
        :param user_metadata: user metadata
        :param data_iter: an iterator to read data
        :param data_fd: a file descriptor to read data
        :param options: a dictionaly which stores gateway specific options.
        :raises ValueError: when some of the required options (storlet_main
                            and file_manager) are missing
        """
        super(DockerStorletRequest, self).__init__(
            storlet_id, params, user_metadata, data_iter, data_fd,
            options=options)

        self.generate_log = self.options.get('generate_log', False)

        self.storlet_main = self.options['storlet_main']
        self.storlet_language = self.options['storlet_language']
        self.storlet_language_version = \
            self.options.get('storlet_language_version')

        if self.options.get('storlet_dependency'):
            self.dependencies = [
                x.strip() for x
                in self.options['storlet_dependency'].split(',')
                if x.strip()]
        else:
            self.dependencies = []

        self.file_manager = self.options['file_manager']

        self.start = self.options.get('range_start')
        self.end = self.options.get('range_end')

    @property
    def has_range(self):
        """
        Whether the input range is given
        """
        return self.start is not None and self.end is not None


class StorletGatewayDocker(StorletGatewayBase):

    request_class = DockerStorletRequest

    def __init__(self, conf, logger, scope):
        """
        :param conf: a dict for gateway conf
        :param logger: a logger instance
        :param scope: scope name to identify the container
        """
        super(StorletGatewayDocker, self).__init__(conf, logger, scope)
        self.storlet_timeout = int(self.conf.get('storlet_timeout', 40))
        self.paths = RunTimePaths(scope, conf)

    @classmethod
    def validate_storlet_registration(cls, params, name):
        """
        Validate required parameters for storlet file

        :param params: parameters related to the storlet file
        :param name: name of the storlet file
        :raises ValueError: if some of the required parameters are missing,
                            or some of the parameters are invalid
        """
        mandatory = ['Language', 'Interface-Version', 'Object-Metadata',
                     'Main']
        cls._check_mandatory_params(params, mandatory)

        if params['Language'].lower() == 'java':
            if '-' not in name or '.' not in name:
                raise ValueError('Storlet name is incorrect')
        elif params['Language'].lower() == 'python':
            # support both py2 and py3
            try:
                version = int(float(params.get('Language-Version', 2)))
            except ValueError:
                raise ValueError('Language-Version is invalid')

            if version not in [2, DEFAULT_PY2, 3, DEFAULT_PY3]:
                # TODO(kota_): more strict version check should be nice.
                raise ValueError('Not supported version specified')

            if name.endswith('.py'):
                cls_name = params['Main']
                if not cls_name.startswith(name[:-3] + '.'):
                    raise ValueError('Main class should be included in '
                                     'storlet file')

                if len(cls_name.split('.')) != 2:
                    raise ValueError('Submodule is currently not supported')
            # TODO(takashi): Add support for sdist tar.gz
            else:
                raise ValueError('Storlet name is incorrect')
        else:
            raise ValueError('Unsupported Language')

        dep = params.get('Dependency')
        if dep:
            deps = dep.split(',')
            if name in deps:
                raise ValueError('Using the same name for storlet and '
                                 'dependency is not allowed')
            if len(deps) != len(set(deps)):
                raise ValueError('Duplicated name in dependencies')

    @classmethod
    def validate_dependency_registration(cls, params, name):
        """
        Validate required parameters for dependency file

        :param params: parameters related to the dependency file
        :param name: name of the dependency file
        :raises ValueError: if some of the required parameters are missing,
                            or some of the parameters are invalid
        """
        mandatory = ['Dependency-Version']
        cls._check_mandatory_params(params, mandatory)

        perm = params.get('Dependency-Permissions')
        if perm is not None:
            try:
                perm_int = int(perm, 8)
            except ValueError:
                raise ValueError('Dependency permission is incorrect')
            if (perm_int & int('600', 8)) != int('600', 8):
                raise ValueError('The owner should have rw permission')

    @classmethod
    def _check_mandatory_params(cls, params, mandatory):
        """
        Ensure that we have all mandatory parameters in the given parameters

        :param params: file parameters
        :param mandatory: required parameters
        :raises ValueError: if some of the required parameters are missing
        """
        for md in mandatory:
            if md not in params:
                raise ValueError('Mandatory parameter is missing'
                                 ': {0}'.format(md))

    def invocation_flow(self, sreq, extra_sources=None):
        """
        Invoke the backend protocl with gateway

        :param sreq: StorletRequest instance
        :param extra_sources (WIP): A list of StorletRequest instance to gather
                                    as extra resoureces to feed to storlet
                                    container as data source
        :return: StorletResponse instance
        """
        run_time_sbox = RunTimeSandbox(self.scope, self.conf, self.logger)
        docker_updated = self.update_docker_container_from_cache(sreq)
        run_time_sbox.activate_storlet_daemon(sreq, docker_updated)
        self._add_system_params(sreq)

        slog_path = self.paths.get_host_slog_path(sreq.storlet_main)
        storlet_pipe_path = \
            self.paths.get_host_storlet_pipe(sreq.storlet_main)

        sprotocol = StorletInvocationProtocol(sreq,
                                              storlet_pipe_path,
                                              slog_path,
                                              self.storlet_timeout,
                                              self.logger,
                                              extra_sources=extra_sources)

        sresp = sprotocol.communicate()

        self._upload_storlet_logs(slog_path, sreq)

        return sresp

    def _add_system_params(self, sreq):
        """
        Adds Storlet engine specific parameters to the invocation

        currently, this consists only of the execution path of the
        Storlet within the Docker container.

        :params params: Request parameters
        """
        sreq.params['storlet_execution_path'] = self. \
            paths.get_sbox_storlet_dir(sreq.storlet_main)

    def _upload_storlet_logs(self, slog_path, sreq):
        """
        Upload storlet execution log as a swift object

        :param slog_path: target path
        :params sreq: DockerStorletRequest instance
        """
        if sreq.generate_log:
            with open(slog_path, 'r') as logfile:
                storlet_name = sreq.storlet_id.split('-')[0]
                log_obj_name = '%s.log' % storlet_name
                sreq.file_manager.put_log(log_obj_name, logfile)

    def bring_from_cache(self, obj_name, sreq, is_storlet):
        """
        Auxiliary function that:

        (1) Brings from Swift obj_name, either this is in a
            storlet or a storlet dependency.
        (2) Copies from local cache into the Docker conrainer
        If this is a Storlet then also validates that the cache is updated
        with most recent copy of the Storlet compared to the copy residing in
        Swift.

        :params obj_name: name of the object
        :params sreq: DockerStorletRequest instance
        :params is_storlet: True if the object is a storlet object
                            False if the object is a dependency object
        :returns: Wheather the Docker container was updated with obj_name
        """
        # Determine the cache we are to work with
        # e.g. dependency or storlet
        if is_storlet:
            cache_dir = self.paths.host_storlet_cache_dir
            get_func = sreq.file_manager.get_storlet
        else:
            cache_dir = self.paths.host_dependency_cache_dir
            get_func = sreq.file_manager.get_dependency

        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, 0o755)

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
            fstat = os.stat(cache_target_path)
            storlet_or_size = int(
                sreq.options['storlet_content_length'].rstrip("L"))
            storlet_or_time = float(sreq.options['storlet_x_timestamp'])
            b_storlet_size_changed = fstat.st_size != storlet_or_size
            b_storlet_file_updated = float(fstat.st_mtime) < storlet_or_time
            if b_storlet_size_changed or b_storlet_file_updated:
                update_cache = True

        if update_cache:
            # If the cache needs to be updated, then get on with it
            # bring the object from storge
            data_iter, perm = get_func(obj_name)

            # TODO(takashi): Do not directly write to target path
            with open(cache_target_path, 'w') as fn:
                for data in data_iter:
                    fn.write(data)

            if not is_storlet:
                if not perm:
                    perm = '0600'
                os.chmod(cache_target_path, int(perm, 8))

        # The node's local cache is now updated.
        # We now verify if we need to update the
        # Docker container itself.
        # The Docker container needs to be updated if:
        # 1. The Docker container does not hold a copy of the object
        # 2. The Docker container holds an older version of the object
        update_docker = False
        docker_storlet_path = \
            self.paths.get_host_storlet_dir(sreq.storlet_main)
        docker_target_path = os.path.join(docker_storlet_path, obj_name)

        if not os.path.exists(docker_storlet_path):
            os.makedirs(docker_storlet_path, 0o755)
            update_docker = True
        elif not os.path.isfile(docker_target_path):
            update_docker = True
        else:
            fstat_cached_object = os.stat(cache_target_path)
            fstat_docker_object = os.stat(docker_target_path)
            b_size_changed = fstat_cached_object.st_size \
                != fstat_docker_object.st_size
            b_time_changed = float(fstat_cached_object.st_mtime) < \
                float(fstat_docker_object.st_mtime)
            if (b_size_changed or b_time_changed):
                update_docker = True

        if update_docker:
            # need to copy from cache to docker
            # copy2 also copies the permissions
            shutil.copy2(cache_target_path, docker_target_path)

        return update_docker

    def update_docker_container_from_cache(self, sreq):
        """
        Iterates over the storlet name and its dependencies appearing

        in the invocation data and make sure they are brought to the
        local cache, and from there to the Docker container.
        Uses the bring_from_cache auxiliary function.

        :params sreq: DockerStorletRequest instance
        :returns: True if the Docker container was updated
        """
        # where at the host side, reside the storlet containers
        storlet_path = self.paths.host_storlet_base_dir
        if not os.path.exists(storlet_path):
            os.makedirs(storlet_path, 0o755)

        # Iterate over storlet and dependencies, and make sure
        # they are updated within the Docker container.
        # return True if any of them wea actually
        # updated within the Docker container
        docker_updated = False

        updated = self.bring_from_cache(sreq.storlet_id, sreq, True)
        docker_updated = docker_updated or updated

        for dep in sreq.dependencies:
            updated = self.bring_from_cache(dep, sreq, False)
            docker_updated = docker_updated or updated

        return docker_updated
