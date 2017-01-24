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

import errno
import os
import select
import stat
import subprocess
import sys
import time
import six

import eventlet
import json
from contextlib import contextmanager

from storlets.sbus import SBus
from storlets.sbus.command import SBUS_CMD_EXECUTE
from storlets.sbus.datagram import SBusFileDescriptor, SBusExecuteDatagram
from storlets.sbus import file_description as sbus_fd
from storlets.sbus.client import SBusClient
from storlets.sbus.client.exceptions import SBusClientException
from storlets.gateway.common.exceptions import StorletRuntimeException, \
    StorletTimeout
from storlets.gateway.common.logger import StorletLogger
from storlets.gateway.common.stob import StorletResponse

MAX_METADATA_SIZE = 4096


eventlet.monkey_patch()


"""---------------------------------------------------------------------------
Sandbox API
"""


class RunTimePaths(object):
    """
    The Storlet Engine need to be access stuff located in many paths:

    1. The various communication channels represented as pipes in the
       filesystem
    2. Directories where to place Storlets
    3. Directories where to place logs

    Communication channels
    ----------------------
    The RunTimeSandbox communicates with the Sandbox via two types of pipes
    1. factory pipe - defined per scope, used for communication with the
       sandbox
       for e.g. start/stop a storlet daemon
    2. Storlet pipe - defined per scope and Storlet, used for communication
       with a storlet daemon, e.g. to call the invoke API

    Each pipe type has two paths:
    1. A path that is inside the sandbox
    2. A path that is outside of the sandbox or at the host side. As such
       this path is prefixed by 'host_'

    Thus, we have the following 4 paths of interest:
    1. sandbox_factory_pipe_path
    2. host_factory_pipe_path
    3. sandbox_storlet_pipe_path
    4. host_storlet_pipe_path

    Our implementation uses the following path structure for the various pipes:
    In the host, all pipes belonging to a given scope are prefixed by
    <pipes_dir>/<scope>, where <pipes_dir> comes from the configuration
    Thus:
    host_factory_pipe_path is of the form <pipes_dir>/<scope>/factory_pipe
    host_storlet_pipe_path is of the form <pipes_dir>/<scope>/<storlet_id>

    In The sandbox side
    sandbox_factory_pipe_path is of the form /mnt/channels/factory_pipe
    sandbox_storlet_pipe_path is of the form  /mnt/channels/<storlet_id>

    Storlets Locations
    ------------------
    The Storlet binaries are accessible from the sandbox using a mounted
    directory.
    This directory is called the storlet directories.
    On the host side it is of the form <storlet_dir>/<scope>/<storlet_name>
    On the sandbox side it is of the form /home/swift/<storlet_name>
    <storlet_dir> comes from the configuration
    <storlet_name> is the prefix of the jar.

    Logs
    ----
    Logs are located in paths of the form:
    <log_dir>/<scope>/<storlet_name>.log
    """

    def __init__(self, scope, conf):
        """
        Constract RunTimePaths instance

        :param scope: scope name to be used as container name
        :param conf: gateway conf
        """
        self.scope = scope
        self.factory_pipe_name = 'factory_pipe'
        self.sandbox_pipe_dir = '/mnt/channels'

        self.sandbox_storlet_base_dir = '/home/swift'
        self.host_root_dir = conf.get('host_root', '/home/docker_device')
        self.host_pipe_root_dir = \
            conf.get('pipes_dir',
                     os.path.join(self.host_root_dir, 'pipes', 'scopes'))
        self.host_storlet_root_dir = \
            conf.get('storlets_dir',
                     os.path.join(self.host_root_dir, 'storlets', 'scopes'))
        self.host_log_root_dir = \
            conf.get('log_dir',
                     os.path.join(self.host_root_dir, 'logs', 'scopes'))
        self.host_cache_root_dir = \
            conf.get('cache_dir',
                     os.path.join(self.host_root_dir, 'cache', 'scopes'))
        self.host_restart_script_dir = \
            conf.get('script_dir',
                     os.path.join(self.host_root_dir, 'scripts'))

        self.host_storlet_python_lib_dir = ('/usr/local/lib/python2.7/'
                                            'dist-packages/storlets')
        self.sandbox_storlet_python_lib_dir = ('/usr/local/lib/python2.7/'
                                               'dist-packages/storlets')
        self.host_storlet_native_lib_dir = '/usr/local/lib/storlets'
        self.sandbox_storlet_native_lib_dir = '/usr/local/lib/storlets'
        self.host_storlet_native_bin_dir = '/usr/local/libexec/storlets'
        self.sandbox_storlet_native_bin_dir = '/usr/local/libexec/storlets'

    @property
    def host_pipe_dir(self):
        return os.path.join(self.host_pipe_root_dir, self.scope)

    def create_host_pipe_dir(self):
        path = self.host_pipe_dir
        if not os.path.exists(path):
            os.makedirs(path)
        # 0777 should be 0700 when we get user namespaces in Docker
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        return path

    @property
    def host_factory_pipe(self):
        return os.path.join(self.host_pipe_dir, self.factory_pipe_name)

    def get_host_storlet_pipe(self, storlet_id):
        return os.path.join(self.host_pipe_dir, storlet_id)

    def get_sbox_storlet_pipe(self, storlet_id):
        return os.path.join(self.sandbox_pipe_dir, storlet_id)

    def get_sbox_storlet_dir(self, storlet_id):
        return os.path.join(self.sandbox_storlet_base_dir, storlet_id)

    @property
    def host_storlet_base_dir(self):
        return os.path.join(self.host_storlet_root_dir, self.scope)

    def get_host_storlet_dir(self, storlet_id):
        return os.path.join(self.host_storlet_base_dir, storlet_id)

    def get_host_slog_path(self, storlet_id):
        return os.path.join(
            self.host_log_root_dir, self.scope, storlet_id,
            'storlet_invoke.log')

    @property
    def host_storlet_cache_dir(self):
        return os.path.join(self.host_cache_root_dir, self.scope, 'storlet')

    @property
    def host_dependency_cache_dir(self):
        return os.path.join(self.host_cache_root_dir, self.scope, 'dependency')

"""---------------------------------------------------------------------------
Docker Stateful Container API
The RunTimeSandbox serve as an API between the Docker Gateway and
a re-usable per scope sandbox
---------------------------------------------------------------------------"""


class RunTimeSandbox(object):
    """
    The RunTimeSandbox represents a re-usable per scope sandbox.

    The sandbox is re-usable in the sense that it can run several storlet
    daemons.

    The following methods are supported:
    ping - pings the sandbox for liveness
    wait - wait for the sandbox to be ready for processing commands
    restart - restart the sandbox
    start_storlet_daemon - start a daemon for a given storlet
    stop_storlet_daemon - stop a daemon of a given storlet
    get_storlet_daemon_status - test if a given storlet daemon is running
    """

    def __init__(self, scope, conf, logger):
        """
        :param scope: scope name to be used as container name
        :param conf: gateway conf
        :param logger: logger instance
        """
        self.paths = RunTimePaths(scope, conf)
        self.scope = scope

        self.sandbox_ping_interval = 0.5
        self.sandbox_wait_timeout = \
            int(conf.get('restart_linux_container_timeout', 10))

        self.docker_repo = conf.get('docker_repo', '')
        self.docker_image_name_prefix = 'tenant'

        # TODO(add line in conf)
        self.storlet_daemon_thread_pool_size = \
            int(conf.get('storlet_daemon_thread_pool_size', 5))
        self.storlet_daemon_debug_level = \
            conf.get('storlet_daemon_debug_level', 'DEBUG')

        # TODO(change logger's route if possible)
        self.logger = logger

        self.default_docker_image_name = \
            conf.get('default_docker_image_name', 'ubuntu_18.04_jre8_storlets')

    def ping(self):
        """
        Ping to daemon factory process inside container

        :returns:  1 when the daemon factory is responsive
                   0 when the daemon factory is not responsive
                  -1 when it fails to send command to the process
        """
        pipe_path = self.paths.host_factory_pipe
        client = SBusClient(pipe_path)
        try:
            resp = client.ping()
            if resp.status:
                return 1
            else:
                self.logger.error('Failed to ping to daemon factory: %s' %
                                  resp.message)
                return 0
        except SBusClientException:
            return -1

    def wait(self):
        """
        Wait while scope's sandbox is starting

        :raises StorletTimeout: the sandbox has not started in
                                sandbox_wait_timeout
        """
        try:
            with StorletTimeout(self.sandbox_wait_timeout):
                while True:
                    rc = self.ping()
                    if (rc != 1):
                        time.sleep(self.sandbox_ping_interval)
                        continue
                    else:
                        return
        except StorletTimeout:
            self.logger.exception("wait for sandbox %s timedout"
                                  % self.scope)
            raise

    def _restart(self, docker_image_name):
        """
        Restarts the scope's sandbox using the specified docker image

        :param docker_image_name: name of the docker image to start
        :raises StorletRuntimeException: when failed to restart the container
        """
        if self.docker_repo:
            docker_image_name = '%s/%s' % (self.docker_repo,
                                           docker_image_name)

        docker_container_name = '%s_%s' % (self.docker_image_name_prefix,
                                           self.scope)

        pipe_mount = '%s:%s' % (self.paths.host_pipe_dir,
                                self.paths.sandbox_pipe_dir)
        storlet_mount = '%s:%s:ro' % (self.paths.host_storlet_base_dir,
                                      self.paths.sandbox_storlet_base_dir)
        storlet_python_lib_mount = '%s:%s:ro' % (
            self.paths.host_storlet_python_lib_dir,
            self.paths.sandbox_storlet_python_lib_dir)
        storlet_native_lib_mount = '%s:%s:ro' % (
            self.paths.host_storlet_native_lib_dir,
            self.paths.sandbox_storlet_native_lib_dir)
        storlet_native_bin_mount = '%s:%s:ro' % (
            self.paths.host_storlet_native_bin_dir,
            self.paths.sandbox_storlet_native_bin_dir)

        cmd = [os.path.join(self.paths.host_restart_script_dir,
                            'restart_docker_container'),
               docker_container_name, docker_image_name, pipe_mount,
               storlet_mount, storlet_python_lib_mount,
               storlet_native_lib_mount, storlet_native_bin_mount]

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()

        if stdout:
            self.logger.debug('STDOUT: %s' % stdout.replace('\n', '#012'))
        if stderr:
            self.logger.error('STDERR: %s' % stderr.replace('\n', '#012'))

        if proc.returncode:
            raise StorletRuntimeException('Failed to restart docker container')

    def restart(self):
        """
        Restarts the scope's sandbox

        """
        self.paths.create_host_pipe_dir()

        docker_image_name = self.scope
        try:
            self._restart(docker_image_name)
            self.wait()
        except StorletTimeout:
            raise
        except StorletRuntimeException:
            # We were unable to start docker container from the tenant image.
            # Let us try to start docker container from default image.
            self.logger.exception("Failed to start docker container from "
                                  "tenant image %s" % docker_image_name)

            self.logger.info("Trying to start docker container from default "
                             "image: %s" % self.default_docker_image_name)
            self._restart(self.default_docker_image_name)
            self.wait()

    def start_storlet_daemon(
            self, spath, storlet_id, language, language_version=None):
        """
        Start SDaemon process in the scope's sandbox
        """
        pipe_path = self.paths.host_factory_pipe
        client = SBusClient(pipe_path)
        try:
            resp = client.start_daemon(
                language.lower(), spath, storlet_id,
                self.paths.get_sbox_storlet_pipe(storlet_id),
                self.storlet_daemon_debug_level,
                self.storlet_daemon_thread_pool_size,
                language_version)

            if resp.status:
                return 1
            else:
                self.logger.error('Failed to start storlet daemon: %s' %
                                  resp.message)
                return 0
        except SBusClientException:
            return -1

    def stop_storlet_daemon(self, storlet_id):
        """
        Stop SDaemon process in the scope's sandbox
        """
        pipe_path = self.paths.host_factory_pipe
        client = SBusClient(pipe_path)
        try:
            resp = client.stop_daemon(storlet_id)
            if resp.status:
                return 1
            else:
                self.logger.error('Failed to stop storlet daemon: %s' %
                                  resp.message)
                return 0
        except SBusClientException:
            return -1

    def get_storlet_daemon_status(self, storlet_id):
        """
        Get the status of SDaemon process in the scope's sandbox
        """
        pipe_path = self.paths.host_factory_pipe
        client = SBusClient(pipe_path)
        try:
            resp = client.daemon_status(storlet_id)
            if resp.status:
                return 1
            else:
                self.logger.error('Failed to get status about storlet '
                                  'daemon: %s' % resp.message)
                return 0
        except SBusClientException:
            return -1

    def _get_storlet_classpath(self, storlet_main, storlet_id, dependencies):
        """
        Get classpath required to run storlet application

        :param storlet_main: Main class name of the storlet
        :param storlet_id: Name of the storlet file
        :param dependencies: A list of dependency file
        :returns: classpath string
        """
        class_path = os.path.join(
            self.paths.get_sbox_storlet_dir(storlet_main), storlet_id)

        dep_path_list = \
            [os.path.join(self.paths.get_sbox_storlet_dir(storlet_main), dep)
             for dep in dependencies]

        return class_path + ':' + ':'.join(dep_path_list)

    def activate_storlet_daemon(self, sreq, cache_updated=True):
        storlet_daemon_status = \
            self.get_storlet_daemon_status(sreq.storlet_main)
        if (storlet_daemon_status == -1):
            # We failed to send a command to the factory.
            # Best we can do is execute the container.
            self.logger.debug('Failed to check Storlet daemon status, '
                              'restart Docker container')
            self.restart()
            storlet_daemon_status = 0

        if (cache_updated is True and storlet_daemon_status == 1):
            # The cache was updated while the daemon is running we need to
            # stop it.
            self.logger.debug('The cache was updated, and the storlet daemon '
                              'is running. Stopping daemon')
            res = self.stop_storlet_daemon(sreq.storlet_main)
            if res != 1:
                self.restart()
            else:
                self.logger.debug('Deamon stopped')
            storlet_daemon_status = 0

        if (storlet_daemon_status == 0):
            self.logger.debug('Going to start storlet daemon!')

            # TODO(takashi): This is not needed for python application
            classpath = self._get_storlet_classpath(
                sreq.storlet_main, sreq.storlet_id, sreq.dependencies)

            daemon_status = self.start_storlet_daemon(
                classpath, sreq.storlet_main, sreq.storlet_language,
                sreq.storlet_language_version)

            if daemon_status != 1:
                self.logger.error('Daemon start Failed, returned code is %d' %
                                  daemon_status)
                raise StorletRuntimeException('Daemon start failed')
            else:
                self.logger.debug('Daemon started')

"""---------------------------------------------------------------------------
Storlet Daemon API
StorletInvocationProtocol
server as an API between the Docker Gateway and the Storlet Daemon which
runs inside the Docker container. These classes implement the Storlet execution
protocol
---------------------------------------------------------------------------"""


class StorletInvocationProtocol(object):
    """
    StorletInvocationProtocol class

    This class serves communictaion with a Docker container to run an
    application

    :param srequest: StorletRequest instance
    :param storlet_pipe_path: path string to pipe
    :param storlet_logger_path: path string to log file
    :param timeout: integer of timeout for waiting the resp from container
    :param logger: logger instance
    :param extra_sources (WIP): a list of StorletRequest instances
                                which keep data_iter for adding extra source
                                as data stream
    """
    def __init__(self, srequest, storlet_pipe_path, storlet_logger_path,
                 timeout, logger, extra_sources=None):
        self.srequest = srequest
        self.storlet_pipe_path = storlet_pipe_path
        self.storlet_logger = StorletLogger(storlet_logger_path)
        self.logger = logger
        self.timeout = timeout

        # local side file descriptors
        self.data_read_fd = None
        self.data_write_fd = None
        self.metadata_read_fd = None
        self.metadata_write_fd = None
        self.taskid_read_fd = None
        self.taskid_write_fd = None
        self.task_id = None
        self._input_data_read_fd = None
        self._input_data_write_fd = None

        self.extra_data_sources = []
        extra_sources = extra_sources or []
        for source in extra_sources:
            if source.has_fd:
                # TODO(kota_): it may be data_fd in the future.
                raise Exception(
                    'extra_source no requires data_fd just data_iter')
            self.extra_data_sources.append(
                {'read_fd': None, 'write_fd': None,
                 'user_metadata': source.user_metadata,
                 'data_iter': source.data_iter})

    @property
    def input_data_read_fd(self):
        """
        File descriptor to read the input body content
        """
        if self.srequest.has_fd:
            return self.srequest.data_fd
        else:
            return self._input_data_read_fd

    @property
    def remote_fds(self):
        """
        A list of sbus file descirptors passed to remote side
        """
        storlets_metadata = {}
        if self.srequest.has_range:
            storlets_metadata.update(
                {'start': str(self.srequest.start),
                 'end': str(self.srequest.end)})

        fds = [SBusFileDescriptor(sbus_fd.SBUS_FD_INPUT_OBJECT,
                                  self.input_data_read_fd,
                                  storage_metadata=self.srequest.user_metadata,
                                  storlets_metadata=storlets_metadata),
               SBusFileDescriptor(sbus_fd.SBUS_FD_OUTPUT_TASK_ID,
                                  self.taskid_write_fd),
               SBusFileDescriptor(sbus_fd.SBUS_FD_OUTPUT_OBJECT,
                                  self.data_write_fd),
               SBusFileDescriptor(sbus_fd.SBUS_FD_OUTPUT_OBJECT_METADATA,
                                  self.metadata_write_fd),
               SBusFileDescriptor(sbus_fd.SBUS_FD_LOGGER,
                                  self.storlet_logger.getfd())]

        for source in self.extra_data_sources:
            fd = SBusFileDescriptor(
                sbus_fd.SBUS_FD_INPUT_OBJECT,
                source['read_fd'],
                storage_metadata=source['user_metadata'])
            fds.append(fd)

        return fds

    @contextmanager
    def _activate_invocation_descriptors(self):
        """
        Contextmanager about file descriptors used in storlet invocation

        NOTE: This context manager now only closes remote side fds,
              so you should close local side fds
        """
        self._prepare_invocation_descriptors()
        try:
            yield
        finally:
            self._close_remote_side_descriptors()

    def _prepare_invocation_descriptors(self):
        """
        Create all pipse used for Storlet execution
        """
        if not self.srequest.has_fd:
            self._input_data_read_fd, self._input_data_write_fd = os.pipe()
        self.data_read_fd, self.data_write_fd = os.pipe()
        self.taskid_read_fd, self.taskid_write_fd = os.pipe()
        self.metadata_read_fd, self.metadata_write_fd = os.pipe()

        for source in self.extra_data_sources:
            source['read_fd'], source['write_fd'] = os.pipe()

    def _safe_close(self, fds):
        """
        Make sure that all of the file descriptors get closed

        :param fds: a list of file descriptors
        """
        for fd in fds:
            try:
                os.close(fd)
            except OSError as err:
                if err.errno != errno.EBADF:
                    raise
                # TODO(kota_): fd might be closed already, so if already
                # closed, OSError will be raised. we need more refactor to
                # keep clean the file discriptors.
                pass

    def _close_remote_side_descriptors(self):
        """
        Close all of the container side descriptors
        """
        fds = [self.data_write_fd, self.metadata_write_fd,
               self.taskid_write_fd]
        if not self.srequest.has_fd:
            fds.append(self.input_data_read_fd)
        fds.extend([source['read_fd'] for source in self.extra_data_sources])
        for fd in fds:
            os.close(fd)

    def _close_local_side_descriptors(self):
        """
        Close all of the host side descriptors
        """
        fds = [self.data_read_fd, self.metadata_read_fd,
               self.taskid_read_fd]
        fds.extend([source['write_fd'] for source in self.extra_data_sources])
        self._safe_close(fds)

    def _cancel(self):
        """
        Cancel on-going storlet execution
        """
        client = SBusClient(self.storlet_pipe_path)
        try:
            resp = client.cancel(self.task_id)
            if not resp.status:
                raise StorletRuntimeException('Failed to cancel task')
        except SBusClientException:
            raise StorletRuntimeException('Failed to cancel task')

    def _invoke(self):
        """
        Send an execution command to the remote daemon factory
        """
        with self.storlet_logger.activate(),\
                self._activate_invocation_descriptors():
            self._send_execute_command()
        self._wait_for_read_with_timeout(self.taskid_read_fd)
        # TODO(kota_): need an assertion for task_id format
        self.task_id = os.read(self.taskid_read_fd, 10)
        os.close(self.taskid_read_fd)

    def _send_execute_command(self):
        """
        Send execute command to the remote daemon factory to invoke storlet
        execution
        """
        dtg = SBusExecuteDatagram(
            SBUS_CMD_EXECUTE,
            self.remote_fds,
            self.srequest.params)
        rc = SBus.send(self.storlet_pipe_path, dtg)

        if (rc < 0):
            raise StorletRuntimeException("Failed to send execute command")

    def _wait_for_read_with_timeout(self, fd):
        """
        Wait while the read file descriptor gets ready

        :param fd: File descriptor to read
        :raises StorletTimeout: Exception raised when it times out to cancel
                                the existing task
        :raises StorletRuntimeException: Exception raised when it fails to
                                         cancel the existing task
        """
        try:
            with StorletTimeout(self.timeout):
                r, w, e = select.select([fd], [], [])
        except StorletTimeout:
            exc_type, exc_value, exc_traceback = sys.exc_info()

            # When there is a task already running, we should cancel it.
            if self.task_id:
                try:
                    self._cancel()
                except StorletRuntimeException:
                    self.logger.warning(
                        'Task %s timed out, but failed to get canceled'
                        % self.task_id)
                    pass

            six.reraise(exc_type, exc_value, exc_traceback)
        if fd not in r:
            raise StorletRuntimeException('Read fd is not ready')

    def _read_metadata(self):
        """
        Read metadata in the storlet execution result from fd

        :returns: a dict of metadata
        """
        self._wait_for_read_with_timeout(self.metadata_read_fd)
        flat_json = os.read(self.metadata_read_fd, MAX_METADATA_SIZE)
        os.close(self.metadata_read_fd)
        try:
            return json.loads(flat_json)
        except ValueError:
            self.logger.exception('Failed to load metadata from json')
            raise StorletRuntimeException('Got invalid format about metadata')

    def _wait_for_write_with_timeout(self, fd):
        """
        Wait while the write file descriptor gets ready

        :param fd: File descriptor to write
        :raises StorletTimeout: Exception raised when it times out to cancel
                                the existing task
        :raises StorletRuntimeException: Exception raised when it fails to
                                         cancel the existing task
        """
        with StorletTimeout(self.timeout):
            r, w, e = select.select([], [fd], [])
        if fd not in w:
            raise StorletRuntimeException('Write fd is not ready')

    def _close_input_data_descriptors(self):
        fds = [self._input_data_read_fd, self._input_data_write_fd]
        self._safe_close(fds)

    def communicate(self):
        try:
            self._invoke()

            if not self.srequest.has_fd:
                self._wait_for_write_with_timeout(self._input_data_write_fd)

                # We do the writing in a different thread.
                # Otherwise, we can run into the following deadlock
                # 1. middleware writes to Storlet
                # 2. Storlet reads and starts to write metadata and then data
                # 3. middleware continues writing
                # 4. Storlet continues writing and gets stuck as middleware
                #    is busy writing, but still not consuming the reader end
                #    of the Storlet writer.
                eventlet.spawn_n(self._write_input_data,
                                 self._input_data_write_fd,
                                 self.srequest.data_iter)

            for source in self.extra_data_sources:
                # NOTE(kota_): not sure right now if using eventlet.spawn_n is
                #              right way. GreenPool is better? I don't get
                #              whole for the dead lock described in above.
                self._wait_for_write_with_timeout(source['write_fd'])
                eventlet.spawn_n(self._write_input_data,
                                 source['write_fd'],
                                 source['data_iter'])

            out_md = self._read_metadata()
            self._wait_for_read_with_timeout(self.data_read_fd)

            return StorletResponse(out_md, data_fd=self.data_read_fd,
                                   cancel=self._cancel)
        except Exception:
            self._close_local_side_descriptors()
            if not self.srequest.has_fd:
                self._close_input_data_descriptors()
            raise

    @contextmanager
    def _open_writer(self, fd):
        with os.fdopen(fd, 'w') as writer:
            yield writer

    def _write_input_data(self, fd, data_iter):
        try:
            # double try/except block saving from unexpected errors
            try:
                with self._open_writer(fd) as writer:
                    for chunk in data_iter:
                        with StorletTimeout(self.timeout):
                            writer.write(chunk)
            except (OSError, TypeError, ValueError):
                self.logger.exception('fdopen failed')
            except IOError:
                # this will happen at sort of broken pipe while writer.write
                self.logger.exception('IOError with writing fd %s' % fd)
            except StorletTimeout:
                self.logger.exception(
                    'Timeout (%s)s with writing fd %s' % (self.timeout, fd))
        except Exception:
            # _write_input_data is designed to run eventlet thread
            # so that we should catch and suppress it here
            self.logger.exception('Unexpected error at writing input data')
