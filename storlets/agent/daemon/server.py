# Copyright (c) 2015-2016 OpenStack Foundation
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
import argparse
import errno
import os
import pwd
import sys
import uuid
import signal
import importlib
from storlets.sbus import SBus
from storlets.agent.common.server import command_handler, EXIT_FAILURE, \
    CommandSuccess, CommandFailure, SBusServer
from storlets.agent.common.utils import get_logger
from storlets.agent.daemon.files import StorletInputFile, \
    StorletRangeInputFile, StorletOutputFile, StorletLogger


class StorletDaemonLoadError(Exception):
    pass


class StorletDaemon(SBusServer):
    """
    An SBusServer implementation for python storlets applications

    :param storlet_name: the program name string which formatted as
                         'module.class'. Note that nested module
                         (e.g. module.submodule.class) is not allowed.
    :param sbus_path: path string to sbus
    :param logger: a logger instance
    :param pool_size: an integer for concurrency running the storlet apps
    """

    def __init__(self, storlet_name, sbus_path, logger, pool_size):
        super(StorletDaemon, self).__init__(sbus_path, logger)

        self.storlet_name = str(storlet_name)
        try:
            module_name, cls_name = self.storlet_name.split('.')
        except ValueError:
            raise ValueError("Invalid storlet name %s" % storlet_name)

        try:
            module = importlib.import_module(module_name)
            self.storlet_cls = getattr(module, cls_name)
        except (ImportError, AttributeError):
            raise StorletDaemonLoadError(
                "Failed to load storlet %s" % self.storlet_name)

        self.pool_size = pool_size
        self.task_id_to_pid = {}
        self.chunk_size = 16

    def _cleanup_pids(self):
        """
        Remove pids which are already terminated
        """
        terminated = []
        for task_id, daemon_pid in self.task_id_to_pid.items():
            try:
                pid, rc = os.waitpid(daemon_pid, os.WNOHANG)
                if pid or rc:
                    terminated.append(task_id)
            except OSError as err:
                if err.errno == errno.ESRCH:
                    terminated.append(task_id)
                if err.errno == errno.ECHILD:
                    # TODO(takashi): Can we skip checking the remaining ones?
                    terminated.append(task_id)
                else:
                    self.logger.exception('Failed to get the status of '
                                          'the subprocess with pid %d' %
                                          daemon_pid)
        for task_id in terminated:
            self.task_id_to_pid.pop(task_id)

    def _remove_pid(self, pid):
        """
        Remove pid from map dict

        :param pid: the pid of the terminated process
        """
        for task_id, daemon_pid in self.task_id_to_pid.items():
            if daemon_pid == pid:
                self.task_id_to_pid.pop(task_id)
                break

    def _wait_child_process(self):
        """
        Wait until the one of the subprocesses gets terminated
        """
        # We save current length of pid map
        prev_num = len(self.task_id_to_pid)

        # First, we need to remove remaining pids of terminated processes
        self._cleanup_pids()
        if not self.task_id_to_pid or len(self.task_id_to_pid) < prev_num:
            # We don't need have to wait here, when we find
            #  1. we do not have any subprocesses
            #  2. some of the subprocesses are already terminated
            # as the result of cleaning up pid map
            return

        try:
            pid = os.wait()[0]
            self._remove_pid(pid)
        except OSError as e:
            if e.errno == errno.ECHILD:
                # Currently we don't have any subprocesses, so reset the dict
                # here
                self.task_id_to_pid = {}
                pass
            else:
                self.logger.exception('Failed to wait existing subprocesses')

    def _wait_all_child_processes(self):
        self.logger.debug('Wait until all of the subprocesses are '
                          'terminated')
        while len(self.task_id_to_pid):
            self._wait_child_process()

    def _safe_close_files(self, files):
        for fobj in files:
            if not fobj.closed:
                self.logger.warning('Fd %d is not closed inside storlet, '
                                    'so close it' % fobj.fileno())
                fobj.close()

    def _create_input_file(self, st_md, in_md, in_fd):
        start = st_md.get('start')
        end = st_md.get('end')
        if start is not None and end is not None:
            return StorletRangeInputFile(in_md, in_fd, int(start), int(end))
        else:
            return StorletInputFile(in_md, in_fd)

    @command_handler
    def execute(self, dtg):
        task_id_out_fd = dtg.task_id_out_fd

        task_id = str(uuid.uuid4())[:8]

        while len(self.task_id_to_pid) >= self.pool_size:
            self._wait_child_process()

        self.logger.debug('Returning task_id: %s ' % task_id)
        with os.fdopen(task_id_out_fd, 'w') as outfile:
            outfile.write(task_id)

        storlet_md = dtg.object_in_storlet_metadata
        params = dtg.params
        in_md = dtg.object_in_metadata
        in_fds = dtg.object_in_fds
        out_md_fds = dtg.object_metadata_out_fds
        out_fds = dtg.object_out_fds
        logger_fd = dtg.logger_out_fd

        pid = os.fork()
        if pid:
            self.logger.debug('Create a subprocess %d for task %s' %
                              (pid, task_id))
            self.task_id_to_pid[task_id] = pid

            for fd in dtg.fds:
                # We do not use fds in main process, so close them
                try:
                    os.close(fd)
                except OSError as e:
                    if e.errno != errno.EBADF:
                        raise
                    pass
        else:
            try:
                self.logger.debug('Start storlet invocation')

                self.logger.debug('in_fds:%s in_md:%s out_md_fds:%s out_fds:%s'
                                  ' logger_fd: %s'
                                  % (in_fds, in_md, out_md_fds, out_fds,
                                     logger_fd))

                in_files = [self._create_input_file(st_md, md, in_fd)
                            for st_md, md, in_fd
                            in zip(storlet_md, in_md, in_fds)]

                out_files = [StorletOutputFile(out_md_fd, out_fd)
                             for out_md_fd, out_fd
                             in zip(out_md_fds, out_fds)]

                self.logger.debug('Start storlet execution')
                with StorletLogger(self.storlet_name, logger_fd) as slogger:
                    handler = self.storlet_cls(slogger)
                    handler(in_files, out_files, params)
                self.logger.debug('Completed')
            except Exception:
                self.logger.exception('Error in storlet invocation')
            finally:
                # Make sure that all fds are closed
                self._safe_close_files(in_files)
                self._safe_close_files(out_files)
                sys.exit()
        return CommandSuccess('OK')

    @command_handler
    def cancel(self, dtg):
        task_id = dtg.task_id
        if task_id not in self.task_id_to_pid:
            return CommandFailure('Task id %s is not found' % task_id, False)

        pid = self.task_id_to_pid.get(task_id)
        try:
            os.kill(pid, signal.SIGTERM)
            self._remove_pid(pid)
            return CommandSuccess('Cancelled task %s' % task_id, False)
        except OSError:
            self.logger.exception('Failed to kill subprocess: %d' % pid)
            return CommandFailure('Failed to cancel task %s' % task_id, False)

    @command_handler
    def halt(self, dtg):
        return CommandSuccess('OK', False)

    def _terminate(self):
        self._wait_all_child_processes()


def main():
    """
    The entry point of daemon_factory process
    """
    parser = argparse.ArgumentParser(
        description='Daemon process to execute storlet applications')
    parser.add_argument('storlet_name', help='storlet name')
    parser.add_argument('sbus_path', help='the path to unix domain socket')
    parser.add_argument('log_level', help='log level')
    parser.add_argument('pool_size', type=int,
                        help='the maximun thread numbers used swapns for '
                             'one storlet application')
    parser.add_argument('container_id', help='container id')
    opts = parser.parse_args()

    # Initialize logger
    logger = get_logger("storlets-daemon", opts.log_level, opts.container_id)
    logger.debug("Storlet Daemon started")
    SBus.start_logger("DEBUG", container_id=opts.container_id)

    # Impersonate the swift user
    pw = pwd.getpwnam('swift')
    os.setresgid(pw.pw_gid, pw.pw_gid, pw.pw_gid)
    os.setresuid(pw.pw_uid, pw.pw_uid, pw.pw_uid)

    # create an instance of storlet daemon
    try:
        daemon = StorletDaemon(opts.storlet_name, opts.sbus_path,
                               logger, opts.pool_size)
    except Exception as err:
        logger.error(err.message)
        return EXIT_FAILURE

    # Start the main loop
    return daemon.main_loop()
