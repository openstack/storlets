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
import signal
import subprocess
import time

from storlets.sbus import SBus
from storlets.sbus.client import SBusClient
from storlets.sbus.client.exceptions import SBusClientException, \
    SBusClientSendError
from storlets.agent.common.server import command_handler, CommandSuccess, \
    CommandFailure, SBusServer
from storlets.agent.common.utils import get_logger, DEFAULT_PY2, DEFAULT_PY3


class SDaemonError(Exception):
    pass


class StorletDaemonFactory(SBusServer):
    """
    An SBusServer implementation for storlets application factory
    """

    def __init__(self, sbus_path, logger, container_id):
        """
        :param sbus_path: Path to the pipe file internal SBus listens to
        :param logger: Logger to dump the information to
        :param container_id: Container id
        """
        super(StorletDaemonFactory, self).__init__(sbus_path, logger)
        self.container_id = container_id
        # Dictionary: map storlet name to pipe name
        self.storlet_name_to_pipe_name = dict()
        # Dictionary: map storlet name to daemon process PID
        self.storlet_name_to_pid = dict()

        self.NUM_OF_TRIES_PINGING_STARTING_DAEMON = 10

    def get_jvm_args(self, daemon_language, storlet_path, storlet_name,
                     pool_size, uds_path, log_level):
        """
        produce the list of arguments for JVM process launch

        :param daemon_language: Language the storlet is written on.
        :param storlet_path: Path to the folder where storlet JRE file is
        :param storlet_name: Storlet main class name
        :param pool_size: Number of threads that storlet daemon's thread
                          pool provides
        :param uds_path: Path to pipe daemon is going to listen to
        :param log_level: Logger verbosity level

        :returns: (A list of the JVM arguments, A list of environ parameters)
        """

        lib_dir = "/usr/local/lib/storlets"
        java_lib_dir = os.path.join(lib_dir, "java")

        jar_deps = ['logback-classic-1.1.2.jar',
                    'logback-core-1.1.2.jar',
                    'slf4j-api-1.7.7.jar',
                    'json_simple-1.1.jar',
                    'SBusJavaFacade.jar',
                    'SCommon.jar',
                    'SDaemon.jar',
                    '']
        jar_deps = [os.path.join(java_lib_dir, x) for x in jar_deps]
        str_dmn_clspth = ':'.join(jar_deps + [storlet_path])
        str_library_path = ':'.join([lib_dir, java_lib_dir])

        str_daemon_main_class = "org.openstack.storlet.daemon.SDaemon"

        if os.environ.get('CLASSPATH'):
            str_dmn_clspth = os.environ['CLASSPATH'] + ':' + str_dmn_clspth

        if os.environ.get('LD_LIBRARY_PATH'):
            str_library_path = os.environ['LD_LIBRARY_PATH'] + ':' + \
                str_library_path

        env = {'CLASSPATH': str_dmn_clspth,
               'LD_LIBRARY_PATH': str_library_path}

        pargs = ['/usr/bin/java', str_daemon_main_class, storlet_name,
                 uds_path, log_level, str(pool_size), self.container_id]
        return pargs, env

    def get_python_args(self, daemon_language, storlet_path, storlet_name,
                        pool_size, uds_path, log_level,
                        daemon_language_version):
        daemon_language_version = daemon_language_version or 2
        if int(float(daemon_language_version)) == 3:
            daemon_language_version = DEFAULT_PY3
        else:
            daemon_language_version = DEFAULT_PY2

        python_interpreter = '/usr/bin/python%s' % daemon_language_version
        str_daemon_main_file = '/usr/local/libexec/storlets/storlets-daemon'
        pargs = [python_interpreter, str_daemon_main_file, storlet_name,
                 uds_path, log_level, str(pool_size), self.container_id]

        python_path = os.path.join('/home/swift/', storlet_name)
        if os.environ.get('PYTHONPATH'):
            python_path = os.environ['PYTHONPATH'] + ':' + python_path
        env = {'PYTHONPATH': python_path}
        return pargs, env

    def spawn_subprocess(self, pargs, env, storlet_name):
        """
        Launch a JVM process for some storlet daemon

        :param pargs: Arguments for the JVM
        :param env: Environment value
        :param storlet_name: Name of the storlet to be executed

        :raises StorletDaemonError: when it fails to start subprocess, or it
                                    can not check the status of the subprocess
                                    launched
        """
        str_pargs = ' '.join(pargs)
        self.logger.debug('Starting subprocess: pargs:{0} env:{1}'
                          .format(str_pargs, env))
        # TODO(takashi): We had better use contextmanager
        # TODO(takashi): Where is this closed?
        try:
            dn = open(os.devnull, 'w')
            daemon_p = subprocess.Popen(
                pargs, stdout=dn, stderr=subprocess.PIPE,
                close_fds=True, shell=False, env=env)
            logger_p = subprocess.Popen(
                'logger', stdin=daemon_p.stderr, stdout=dn, stderr=dn,
                close_fds=True, shell=False)
        except OSError:
            self.logger.exception('Unable to start subprocess')
            raise SDaemonError('Unable to start the storlet daemon {0}'.
                               format(storlet_name))

        # Wait for the storlet daemon initializes itself
        time.sleep(1)
        self.logger.debug('Started the storlet daemon {0} with pid {1}'
                          .format(daemon_p.pid, logger_p.pid))

        # Does the storlet daemon keep running?
        try:
            status = self.get_process_status_by_pid(daemon_p.pid,
                                                    storlet_name)
        except SDaemonError:
            raise SDaemonError('The storlet daemon {0} is terminated'
                               .format(storlet_name))

        if status:
            # Keep PID of the storlet daemon subprocess
            self.storlet_name_to_pid[storlet_name] = daemon_p.pid
            if not self.wait_for_daemon_to_initialize(storlet_name):
                raise SDaemonError('No response from the storlet daemon '
                                   '{0}'.format(storlet_name))
        else:
            self.logger.error('Started the storlet daemon for {0}, but '
                              'can not check its status'.
                              format(storlet_name))
            raise SDaemonError('The storlet daemon {0} is started '
                               'but not responsive'.format(storlet_name))

    def wait_for_daemon_to_initialize(self, storlet_name):
        """
        Send a Ping service datagram. Validate that
        Daemon response is correct. Give up after the
        predefined number of attempts (5)

        :param storlet_name: Storlet name we are checking the daemon for
        :returns: daemon status (True, False)
        """
        storlet_pipe_name = self.storlet_name_to_pipe_name[storlet_name]
        self.logger.debug('Send PING command to {0} via {1}'.
                          format(storlet_name, storlet_pipe_name))
        client = SBusClient(storlet_pipe_name)
        for i in range(self.NUM_OF_TRIES_PINGING_STARTING_DAEMON):
            try:
                resp = client.ping()
                if resp.status:
                    return True
            except SBusClientSendError:
                pass
            except SBusClientException:
                self.logger.exception('Failed to send sbus command')
                break
            time.sleep(1)
        return False

    def process_start_daemon(self, daemon_language, storlet_path, storlet_name,
                             pool_size, uds_path, log_level,
                             daemon_language_version=None):
        """
        Start storlet daemon process

        :param daemon_language: Language the storlet is written on.
                                Now Java and Python are supported.
        :param storlet_path: Path to the folder where storlet JRE file is
        :param storlet_name: Storlet main class name
        :param pool_size: Number of threads that storlet daemon's thread
                          pool provides
        :param uds_path: Path to pipe daemon is going to listen to
        :param log_level: Logger verbosity level
        :param daemon_language_version: daemon language version (e.g. py2, py3)
            only python lang supports this option

        :returns: True if it starts a new subprocess
                  False if there already exists a running process
        """
        if daemon_language.lower() == 'java':
            pargs, env = self.get_jvm_args(
                daemon_language, storlet_path, storlet_name,
                pool_size, uds_path, log_level)
        elif daemon_language.lower() == 'python':
            pargs, env = self.get_python_args(
                daemon_language, storlet_path, storlet_name,
                pool_size, uds_path, log_level, daemon_language_version)
        else:
            raise SDaemonError(
                'Got unsupported daemon language: %s' % daemon_language)

        self.logger.debug('Assigning storlet_name_to_pipe_name[{0}]={1}'.
                          format(storlet_name, uds_path))
        self.storlet_name_to_pipe_name[storlet_name] = uds_path

        self.logger.debug('Validating that {0} is not already running'.
                          format(storlet_name))
        if self.get_process_status_by_name(storlet_name):
            self.logger.debug('The storlet daemon for {0} is already running'.
                              format(storlet_name))
            return False
        else:
            self.logger.debug('The storlet daemon {0} is not running. '
                              'Spawn the storlet daemon'.
                              format(storlet_name))
            self.spawn_subprocess(pargs, env, storlet_name)
            return True

    def get_process_status_by_name(self, storlet_name):
        """
        Check if the daemon runs for the specific storlet

        :param storlet_name: Storlet name we are checking the daemon for
        :returns: process status (True/False)
        """
        daemon_pid = self.storlet_name_to_pid.get(storlet_name)
        if daemon_pid is not None:
            return self.get_process_status_by_pid(daemon_pid, storlet_name)
        else:
            self.logger.debug('The storlet daemon {0} is not found in map'.
                              format(storlet_name))
            return False

    def get_process_status_by_pid(self, daemon_pid, storlet_name):
        """
        Check if a process with specific ID runs

        :param daemon_pid:   Storlet daemon process ID
        :param storlet_name: Storlet name we are checking the daemon for
        :returns: process status (True/False)
        """
        self.logger.debug('Get status for the storlet daemon {0}, pid {1}'.
                          format(storlet_name, str(daemon_pid)))
        try:
            pid, rc = os.waitpid(daemon_pid, os.WNOHANG)
            self.logger.debug('Storlet {0}, PID = {1}, ErrCode = {2}'.
                              format(storlet_name, str(pid), str(rc)))
        except OSError as err:
            # If the storlet daemon crashed
            # we may get here ECHILD for which
            # we want to return False
            if err.errno in (errno.ECHILD, errno.ESRCH):
                return False
            elif err.errno == errno.EPERM:
                raise SDaemonError(
                    'No permission to access the storlet daemon {0}'.
                    format(storlet_name))
            else:
                self.logger.exception(
                    'Failed to access the storlet daemon {0}'.
                    format(storlet_name))
                raise SDaemonError('Unknown error')

        if not pid and not rc:
            return True
        else:
            self.logger.debug('The storlet daemon {0} is terminated'
                              .format(storlet_name))
            return False

    def process_kill(self, storlet_name):
        """
        Kill the storlet daemon immediately
        (kill -9 $DMN_PID)

        :param storlet_name: Storlet name we are checking the daemon for
        :returns: (pid, return code)
        :raises SDaemonError: when failed to kill the storlet daemon
        """
        dmn_pid = self.storlet_name_to_pid.get(storlet_name)
        self.logger.debug('Kill the storlet daemon {0} with pid {1}'
                          .format(storlet_name, dmn_pid))

        if dmn_pid is None:
            raise SDaemonError('{0} is not found'.format(storlet_name))

        try:
            os.kill(dmn_pid, signal.SIGKILL)
            obtained_pid, obtained_code = os.waitpid(dmn_pid, os.WNOHANG)
            self.logger.debug(
                'Killed the storlet daemon {0}, PID = {1} ErrCode = {2}'.
                format(storlet_name, obtained_pid, obtained_code))
            self.storlet_name_to_pid.pop(storlet_name)
            return obtained_pid, obtained_code
        except OSError:
            self.logger.exception(
                'Error when sending kill signal to the storlet daemon %s' %
                storlet_name)
            raise SDaemonError('Failed to send kill signal to the storlet '
                               'daemon {0}'.format(storlet_name))

    def process_kill_all(self, try_all=True):
        """
        Kill every one.

        :param try_all: wheather we try to kill all process if we fail to
                        stop some of the storlet daemons
        :raises SDaemonError: when failed to kill one of the storlet daemons
        """
        failed = []
        for storlet_name in list(self.storlet_name_to_pid):
            try:
                self.process_kill(storlet_name)
            except SDaemonError:
                self.logger.exception('Failed to stop the storlet daemon {0}'
                                      .format(storlet_name))
                if try_all:
                    failed.append(storlet_name)
                else:
                    raise
        if failed:
            names = ', '.join(failed)
            raise SDaemonError('Failed to stop some storlet daemons: {0}'
                               .format(names))

    def shutdown_all_processes(self, try_all=True):
        """
        send HALT command to every spawned process

        :param try_all: wheather we try to kill all process if we fail to
                        stop some of the storlet daemons
        :returns: a list of the terminated storlet daemons
        :raises SDaemonError: when failed to kill one of the storlet daemons
        """
        terminated = []
        failed = []
        for storlet_name in list(self.storlet_name_to_pid):
            try:
                self.shutdown_process(storlet_name)
                terminated.append(storlet_name)
            except SDaemonError:
                self.logger.exception('Failed to shutdown storlet daemon {0}'
                                      .format(storlet_name))
                if try_all:
                    failed.append(storlet_name)
                else:
                    raise

        if failed:
            names = ', '.join(failed)
            raise SDaemonError('Failed to shutdown some storlet daemons: {0}'
                               .format(names))
        else:
            self.logger.info('All the storlet daemons are terminated')
            return terminated

    def shutdown_process(self, storlet_name):
        """
        send HALT command to storlet daemon

        :param storlet_name: Storlet name we are checking the daemon for
        :raises SDaemonError: when wailed to shutdown the storlet daemon
        """
        self.logger.debug(
            'Shutdown the storlet daemon {0}'.format(storlet_name))

        dmn_pid = self.storlet_name_to_pid.get(storlet_name)
        self.logger.debug('Storlet Daemon PID is {0}'.format(dmn_pid))
        if dmn_pid is None:
            raise SDaemonError('{0} is not found'.format(storlet_name))

        storlet_pipe_name = self.storlet_name_to_pipe_name[storlet_name]
        self.logger.debug('Send HALT command to {0} via {1}'.
                          format(storlet_name, storlet_pipe_name))

        client = SBusClient(storlet_pipe_name)
        try:
            resp = client.halt()
            if not resp.status:
                self.logger.error('Failed to send sbus command: %s' %
                                  resp.message)
                raise SDaemonError(
                    'Failed to send halt to {0}'.format(storlet_name))

        except SBusClientException:
            self.logger.exception('Failed to send sbus command')
            raise SDaemonError(
                'Failed to send halt command to the storlet daemon {0}'
                .format(storlet_name))

        try:
            os.waitpid(dmn_pid, 0)
            self.storlet_name_to_pid.pop(storlet_name)
        except OSError:
            self.logger.exception(
                'Error when waiting the storlet daemon {0}'.format(
                    storlet_name))
            raise SDaemonError('Failed to wait the storlet daemon {0}'
                               .format(storlet_name))

    @command_handler
    def start_daemon(self, dtg):
        params = dtg.params
        storlet_name = params['storlet_name']
        try:
            if self.process_start_daemon(
                    params['daemon_language'], params['storlet_path'],
                    storlet_name, params['pool_size'],
                    params['uds_path'], params['log_level'],
                    daemon_language_version=params.get(
                        'daemon_language_version')):
                msg = 'OK'
            else:
                msg = '{0} is already running'.format(storlet_name)
            return CommandSuccess(msg)
        except SDaemonError as err:
            self.logger.exception('Failed to start the sdaemon for {0}'
                                  .format(storlet_name))
            return CommandFailure(err.args[0])

    @command_handler
    def stop_daemon(self, dtg):
        params = dtg.params
        storlet_name = params['storlet_name']
        try:
            pid, code = self.process_kill(storlet_name)
            msg = 'Storlet {0}, PID = {1}, ErrCode = {2}'.format(
                storlet_name, pid, code)
            return CommandSuccess(msg)
        except SDaemonError as err:
            self.logger.exception('Failed to kill the storlet daemon %s' %
                                  storlet_name)
            return CommandFailure(err.args[0])

    @command_handler
    def daemon_status(self, dtg):
        params = dtg.params
        storlet_name = params['storlet_name']
        try:
            if self.get_process_status_by_name(storlet_name):
                msg = 'The storlet daemon {0} seems to be OK'.format(
                    storlet_name)
                return CommandSuccess(msg)
            else:
                msg = 'No running storlet daemons for {0}'.format(storlet_name)
                return CommandFailure(msg)
        except SDaemonError as err:
            self.logger.exception('Failed to get status of the storlet '
                                  'daemon %s' % storlet_name)
            return CommandFailure(err.args[0])

    @command_handler
    def stop_daemons(self, dtg):
        try:
            self.process_kill_all()
            return CommandSuccess('OK', False)
        except SDaemonError as err:
            self.logger.exception('Failed to stop some storlet daemons')
            return CommandFailure(err.args[0], False)

    @command_handler
    def halt(self, dtg):
        try:
            terminated = self.shutdown_all_processes()
            msg = '; '.join(['%s: terminated' % x for x in terminated])
            return CommandSuccess(msg, False)
        except SDaemonError as err:
            self.logger.exception('Failed to halt some storlet daemons')
            return CommandFailure(err.args[0], False)

    def _terminate(self):
        pass


def main():
    """
    The entry point of daemon_factory process
    """
    parser = argparse.ArgumentParser(
        description='Factory process to manage storlet daemons')
    parser.add_argument('sbus_path', help='the path to unix domain socket')
    parser.add_argument('log_level', help='log level')
    parser.add_argument('container_id', help='container id')
    opts = parser.parse_args()

    # Initialize logger
    logger = get_logger("daemon-factory", opts.log_level, opts.container_id)
    logger.debug("Daemon factory started")
    SBus.start_logger("DEBUG", container_id=opts.container_id)

    # Impersonate the swift user
    pw = pwd.getpwnam('swift')
    os.setresgid(pw.pw_gid, pw.pw_gid, pw.pw_gid)
    os.setresuid(pw.pw_uid, pw.pw_uid, pw.pw_uid)

    # create an instance of daemon_factory
    factory = StorletDaemonFactory(opts.sbus_path, logger, opts.container_id)

    # Start the main loop
    return factory.main_loop()
