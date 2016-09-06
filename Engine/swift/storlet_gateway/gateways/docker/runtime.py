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

import eventlet
import json
from contextlib import contextmanager

from sbus import SBus
from sbus.datagram import FDMetadata, ClientSBusOutDatagram
from sbus.file_description import SBUS_FD_INPUT_OBJECT, \
    SBUS_FD_LOGGER, SBUS_FD_OUTPUT_OBJECT, SBUS_FD_OUTPUT_OBJECT_METADATA, \
    SBUS_FD_OUTPUT_TASK_ID
from sbus.command import SBUS_CMD_CANCEL, \
    SBUS_CMD_DAEMON_STATUS, SBUS_CMD_EXECUTE, SBUS_CMD_PING, \
    SBUS_CMD_START_DAEMON, SBUS_CMD_STOP_DAEMON
from storlet_gateway.common.exceptions import StorletRuntimeException, \
    StorletTimeout
from storlet_gateway.common.logger import StorletLogger
from storlet_gateway.common.stob import StorletResponse

MAX_METADATA_SIZE = 4096


eventlet.monkey_patch()


@contextmanager
def _open_pipe():
    """
    Context manager for os.pipe
    """
    read_fd, write_fd = os.pipe()
    try:
        yield (read_fd, write_fd)
    finally:
        os.close(read_fd)
        os.close(write_fd)


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
        self.factory_pipe_suffix = 'factory_pipe'
        self.sandbox_pipe_prefix = '/mnt/channels'
        self.storlet_pipe_suffix = '_storlet_pipe'

        self.sandbox_storlet_dir_prefix = '/home/swift'
        self.host_root = conf.get('host_root', '/home/docker_device')
        self.host_pipe_root = \
            conf.get('pipes_dir',
                     os.path.join(self.host_root, 'pipes', 'scopes'))
        self.host_storlet_root = \
            conf.get('storlets_dir',
                     os.path.join(self.host_root, 'storlets', 'scopes'))
        self.host_log_path_root = \
            conf.get('log_dir',
                     os.path.join(self.host_root, 'logs', 'scopes'))
        self.host_cache_root = \
            conf.get('cache_dir',
                     os.path.join(self.host_root, 'cache', 'scopes'))
        self.host_restart_script_dir = \
            conf.get('script_dir',
                     os.path.join(self.host_root, 'scripts'))

    def host_pipe_prefix(self):
        return os.path.join(self.host_pipe_root, self.scope)

    def create_host_pipe_prefix(self):
        path = self.host_pipe_prefix()
        if not os.path.exists(path):
            os.makedirs(path)
        # 0777 should be 0700 when we get user namespaces in Docker
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

    def host_factory_pipe(self):
        return os.path.join(self.host_pipe_prefix(),
                            self.factory_pipe_suffix)

    def host_storlet_pipe(self, storlet_id):
        return os.path.join(self.host_pipe_prefix(),
                            storlet_id)

    def sbox_storlet_pipe(self, storlet_id):
        return os.path.join(self.sandbox_pipe_prefix,
                            storlet_id)

    def sbox_storlet_exec(self, storlet_id):
        return os.path.join(self.sandbox_storlet_dir_prefix, storlet_id)

    def host_storlet_prefix(self):
        return os.path.join(self.host_storlet_root, self.scope)

    def host_storlet(self, storlet_id):
        return os.path.join(self.host_storlet_prefix(), storlet_id)

    def slog_path(self, storlet_id):
        log_dir = os.path.join(self.host_log_path_root, self.scope, storlet_id)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        return log_dir

    def get_host_storlet_cache_dir(self):
        return os.path.join(self.host_cache_root, self.scope, 'storlet')

    def get_host_dependency_cache_dir(self):
        return os.path.join(self.host_cache_root, self.scope, 'dependency')

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
            int(conf.get('restart_linux_container_timeout', 3))

        self.docker_repo = conf.get('docker_repo', 'localhost:5001')
        self.docker_image_name_prefix = 'tenant'

        # TODO(should come from upper layer Storlet metadata)
        self.storlet_language = 'java'

        # TODO(add line in conf)
        self.storlet_daemon_thread_pool_size = \
            int(conf.get('storlet_daemon_thread_pool_size', 5))
        self.storlet_daemon_debug_level = \
            conf.get('storlet_daemon_debug_level', 'TRACE')

        # TODO(change logger's route if possible)
        self.logger = logger

    def _parse_sandbox_factory_answer(self, str_answer):
        """
        Parse answer string recieved from container side

        :param str_answer: answer string
        :returns: (status, message)
        """
        two_tokens = str_answer.split(':', 1)
        b_success = False
        if two_tokens[0] == 'True':
            b_success = True
        return b_success, two_tokens[1]

    def ping(self):
        """
        Ping to daemon factory process inside container

        :returns:  1 when the daemon factory is responsive
                   0 when the daemon factory is not responsive
                  -1 when it fails to send command to the process
        """
        pipe_path = self.paths.host_factory_pipe()

        with _open_pipe() as (read_fd, write_fd):
            dtg = ClientSBusOutDatagram.create_service_datagram(
                SBUS_CMD_PING,
                write_fd)
            rc = SBus.send(pipe_path, dtg)
            if (rc < 0):
                return -1

            reply = os.read(read_fd, 10)

        res, error_txt = self._parse_sandbox_factory_answer(reply)
        if res is True:
            return 1
        return 0

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
        :returns: retruned value of restart_docker_container
        """
        if self.docker_repo:
            docker_image_name = '%s/%s' % (self.docker_repo,
                                           docker_image_name)

        docker_container_name = '%s_%s' % (self.docker_image_name_prefix,
                                           self.scope)

        pipe_mount = '%s:%s' % (self.paths.host_pipe_prefix(),
                                self.paths.sandbox_pipe_prefix)
        storlet_mount = '%s:%s' % (self.paths.host_storlet_prefix(),
                                   self.paths.sandbox_storlet_dir_prefix)

        cmd = [self.paths.host_restart_script_dir +
               '/restart_docker_container',
               docker_container_name, docker_image_name, pipe_mount,
               storlet_mount]

        return subprocess.call(cmd)

    def restart(self):
        """
        Restarts the scope's sandbox

        """
        self.paths.create_host_pipe_prefix()

        docker_image_name = self.scope
        if self._restart(docker_image_name) == 0:
            self.wait()
            return

        # We were unable to start docker container from the tenant image.
        # Let us try to start docker container from default image.
        self.logger.info("Failed to start docker container from tenant image "
                         "%s" % docker_image_name)
        self.logger.info("Trying to start docker container from default image")

        # TODO(eranr): move the default tenant image name to a config var
        docker_image_name = 'ubuntu_14.04_jre8_storlets'
        self._restart(docker_image_name)
        self.wait()

    def start_storlet_daemon(self, spath, storlet_id):
        """
        Start SDaemon process in the scope's sandbox

        """
        prms = {}
        prms['daemon_language'] = 'java'
        prms['storlet_path'] = spath
        prms['storlet_name'] = storlet_id
        prms['uds_path'] = self.paths.sbox_storlet_pipe(storlet_id)
        prms['log_level'] = self.storlet_daemon_debug_level
        prms['pool_size'] = self.storlet_daemon_thread_pool_size

        with _open_pipe() as (read_fd, write_fd):
            dtg = ClientSBusOutDatagram.create_service_datagram(
                SBUS_CMD_START_DAEMON,
                write_fd,
                prms)

            pipe_path = self.paths.host_factory_pipe()
            rc = SBus.send(pipe_path, dtg)
            # TODO(takashi): Why we should rond rc into -1?
            if (rc < 0):
                return -1
            reply = os.read(read_fd, 10)

        res, error_txt = self._parse_sandbox_factory_answer(reply)
        if res is True:
            return 1
        return 0

    def stop_storlet_daemon(self, storlet_id):
        """
        Stop SDaemon process in the scope's sandbox
        """
        with _open_pipe() as (read_fd, write_fd):
            dtg = ClientSBusOutDatagram.create_service_datagram(
                SBUS_CMD_STOP_DAEMON,
                write_fd,
                {'storlet_name': storlet_id})
            pipe_path = self.paths.host_factory_pipe()
            rc = SBus.send(pipe_path, dtg)
            if (rc < 0):
                self.logger.info("Failed to send status command to %s %s" %
                                 (self.scope, storlet_id))
                return -1

            reply = os.read(read_fd, 10)

        res, error_txt = self._parse_sandbox_factory_answer(reply)
        if res is True:
            return 1
        return 0

    def get_storlet_daemon_status(self, storlet_id):
        """
        Get the status of SDaemon process in the scope's sandbox
        """
        with _open_pipe() as (read_fd, write_fd):
            dtg = ClientSBusOutDatagram.create_service_datagram(
                SBUS_CMD_DAEMON_STATUS,
                write_fd,
                {'storlet_name': storlet_id})
            pipe_path = self.paths.host_factory_pipe()
            rc = SBus.send(pipe_path, dtg)
            if (rc < 0):
                self.logger.info("Failed to send status command to %s %s" %
                                 (self.scope, storlet_id))
                return -1
            reply = os.read(read_fd, 10)

        res, error_txt = self._parse_sandbox_factory_answer(reply)
        if res is True:
            return 1
        return 0

    def activate_storlet_daemon(self, sreq, cache_updated=True):
        storlet_daemon_status = \
            self.get_storlet_daemon_status(sreq.storlet_main)
        if (storlet_daemon_status == -1):
            # We failed to send a command to the factory.
            # Best we can do is execute the container.
            self.logger.debug('Failed to check Storlet daemon status, '
                              'restart Docker container')
            try:
                self.restart()
            except StorletTimeout:
                raise StorletRuntimeException('Docker container is '
                                              'not responsive')
            storlet_daemon_status = 0

        if (cache_updated is True and storlet_daemon_status == 1):
            # The cache was updated while the daemon is running we need to
            # stop it.
            self.logger.debug('The cache was updated, and the storlet daemon '
                              'is running. Stopping daemon')
            res = self.stop_storlet_daemon(sreq.storlet_main)
            if res != 1:
                try:
                    self.restart()
                except StorletTimeout:
                    raise StorletRuntimeException('Docker container is '
                                                  'not responsive')
            else:
                self.logger.debug('Deamon stopped')
            storlet_daemon_status = 0

        if (storlet_daemon_status == 0):
            self.logger.debug('Going to start storlet daemon!')
            class_path = \
                '/home/swift/%s/%s' % (sreq.storlet_main, sreq.storlet_id)
            for dep in sreq.dependencies:
                class_path = '%s:/home/swift/%s/%s' % \
                             (class_path, sreq.storlet_main, dep)

            daemon_status = \
                self.start_storlet_daemon(class_path, sreq.storlet_main)

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
    :param storlet_pipe_path:
    :param storlet_logger_path:
    :param timeout:
    """
    def __init__(self, srequest, storlet_pipe_path, storlet_logger_path,
                 timeout):
        self.srequest = srequest
        self.storlet_pipe_path = storlet_pipe_path
        self.storlet_logger_path = storlet_logger_path
        self.storlet_logger = StorletLogger(self.storlet_logger_path,
                                            'storlet_invoke')
        self.timeout = timeout

        # local side file descriptors
        self.data_read_fd = None
        self.data_write_fd = None
        self.metadata_read_fd = None
        self.metadata_write_fd = None
        self.execution_str_read_fd = None
        self.execution_str_write_fd = None
        self.task_id = None

        if not os.path.exists(storlet_logger_path):
            os.makedirs(storlet_logger_path)

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
        File descriptors to be passed to container side
        """
        return [self.input_data_read_fd,
                self.execution_str_write_fd,
                self.data_write_fd,
                self.metadata_write_fd,
                self.storlet_logger.getfd()]

    @property
    def remote_fds_metadata(self):
        """
        Metadata about file descriptors to be passed to container side
        """
        input_fd_metadata = FDMetadata(SBUS_FD_INPUT_OBJECT)
        if self.srequest.user_metadata:
            input_fd_metadata.storage_metadata.update(
                self.srequest.user_metadata)
        if self.srequest.has_range:
            input_fd_metadata.storlets_metadata['start'] = \
                str(self.srequest.start)
            input_fd_metadata.storlets_metadata['end'] = \
                str(self.srequest.end)
        return [input_fd_metadata.to_dict(),
                FDMetadata(SBUS_FD_OUTPUT_TASK_ID).to_dict(),
                FDMetadata(SBUS_FD_OUTPUT_OBJECT).to_dict(),
                FDMetadata(SBUS_FD_OUTPUT_OBJECT_METADATA).to_dict(),
                FDMetadata(SBUS_FD_LOGGER).to_dict()]

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
        self.execution_str_read_fd, self.execution_str_write_fd = os.pipe()
        self.metadata_read_fd, self.metadata_write_fd = os.pipe()

    def _safe_close(self, fds):
        """
        Make sure that all of the file descriptors get closed

        :param fds: a list of file descriptors
        """
        for fd in fds:
            try:
                os.close(fd)
            except OSError as err:
                if err.errno != errno.EBADFD:
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
               self.execution_str_write_fd]
        self._safe_close(fds)

    def _close_local_side_descriptors(self):
        """
        Close all of the host side descriptors
        """
        fds = [self.data_read_fd, self.metadata_read_fd,
               self.execution_str_read_fd]
        self._safe_close(fds)

    def _cancel(self):
        """
        Cancel on-going storlet execution
        """
        with _open_pipe() as (read_fd, write_fd):
            dtg = ClientSBusOutDatagram.create_service_datagram(
                SBUS_CMD_CANCEL,
                write_fd,
                None,
                self.task_id)
            rc = SBus.send(self.storlet_pipe_path, dtg)
            if (rc < 0):
                raise StorletRuntimeException('Failed to cancel task')
            # TODO(takashi): Check the reponse here
            os.read(read_fd, 10)

    def _invoke(self):
        """
        Send an execution command to the remote daemon factory
        """
        dtg = ClientSBusOutDatagram(
            SBUS_CMD_EXECUTE,
            self.remote_fds,
            self.remote_fds_metadata,
            self.srequest.params)
        rc = SBus.send(self.storlet_pipe_path, dtg)

        if (rc < 0):
            raise StorletRuntimeException("Failed to send execute command")

        self._wait_for_read_with_timeout(self.execution_str_read_fd)
        # TODO(kota_): need an assertion for task_id format
        self.task_id = os.read(self.execution_str_read_fd, 10)
        os.close(self.execution_str_read_fd)

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

            # TODO(takashi): this should be replaced by six.rerase
            #                when supporting py3
            raise exc_type, exc_value, exc_traceback
        if fd not in r:
            raise StorletRuntimeException('Read fd is not ready')

    def _read_metadata(self):
        """
        Read metadata in the storlet execution result from fd

        :returns: a dict of metadata
        """
        self._wait_for_read_with_timeout(self.metadata_read_fd)
        flat_json = os.read(self.metadata_read_fd, MAX_METADATA_SIZE)
        if flat_json is None:
            return None
        os.close(self.metadata_read_fd)
        # TODO(takashi): We should validate json format
        return json.loads(flat_json)

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

    def _write_with_timeout(self, writer, chunk):
        try:
            with StorletTimeout(self.timeout):
                writer.write(chunk)
        except StorletTimeout:
            writer.close()
            raise

    def _close_input_data_descriptors(self):
        fds = [self._input_data_read_fd, self._input_data_write_fd]
        self._safe_close(fds)

    def communicate(self):
        try:
            with self.storlet_logger.activate(),\
                    self._activate_invocation_descriptors():
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
                eventlet.spawn_n(self._write_input_data)

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
    def _open_writer(self):
        writer = os.fdopen(self._input_data_write_fd, 'w')
        try:
            yield writer
        finally:
            writer.close()
        # NOTE(takashi): writer.close() also closes fd, so we don't have to
        #                close fd again.

    def _write_input_data(self):
        with self._open_writer() as writer:
            for chunk in self.srequest.data_iter:
                self._write_with_timeout(writer, chunk)
