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

import errno
import logging
from logging.handlers import SysLogHandler
import os
import pwd
import signal
import subprocess
import time

from sbus import SBus
from sbus.datagram import ClientSBusOutDatagram
from sbus.command import SBUS_CMD_PREFIX, \
    SBUS_CMD_HALT, SBUS_CMD_PING


EXIT_SUCCESS = 0
EXIT_FAILURE = 1


class CommandResponse(Exception):
    """
    The result of command execution
    """

    def __init__(self, status, message, iterable=True):
        """
        Constract CommandResponse instance

        :param status: task status
        :param message: message to be returned and logged
        :param iterable: wheter we can keep SDaemon process running
        """
        self.status = status
        self.message = message
        self.iterable = iterable

    @property
    def report_message(self):
        """
        Create log message to be returned to gateway
        """
        return '%s: %s' % (str(self.status), self.message)


class CommandSuccess(CommandResponse):
    def __init__(self, message, iterable=True):
        super(CommandSuccess, self).__init__(True, message, iterable)


class CommandFailure(CommandResponse):
    def __init__(self, message, iterable=True):
        super(CommandFailure, self).__init__(False, message, iterable)


def command_handler(func):
    """
    Decorator for handler functions for command
    """
    func.is_command_handler = True
    return func


class DaemonFactory(object):
    """
    This class acts as the manager for storlet daemons.

    It listens to commands and reacts on them in an internal loop.
    As for now (01-Dec-2014) it is a single thread, synchronous
    processing.
    """

    def __init__(self, path, logger):
        """
        :param path: Path to the pipe file internal SBus listens to
        :param logger: Logger to dump the information to
        """

        self.logger = logger
        self.pipe_path = path
        # Dictionary: map storlet name to pipe name
        self.storlet_name_to_pipe_name = dict()
        # Dictionary: map storlet name to daemon process PID
        self.storlet_name_to_pid = dict()

        self.NUM_OF_TRIES_PINGING_STARTING_DAEMON = 10

    def get_jvm_args(self, daemon_language, storlet_path, storlet_name,
                     pool_size, uds_path, log_level, container_id):
        """
        Check the input parameters, produce the list
        of arguments for JVM process launch

        :param daemon_language: Language the storlet is written on.
                                Now (01-Dec-2014) only Java is supported.
        :param storlet_path: Path to the folder where storlet JRE file is
        :param storlet_name: Storlet main class name
        :param pool_size: Number of threads that storlet daemon's thread
                          pool provides
        :param uds_path: Path to pipe daemon is going to listen to
        :param log_level: Logger verbosity level
        :param container_id: container id

        :returns: (A list of the JVM arguments, A list of environ parameters)
        """

        str_prfx = "/opt/storlets/"

        jar_deps = ['logback-classic-1.1.2.jar',
                    'logback-core-1.1.2.jar',
                    'slf4j-api-1.7.7.jar',
                    'json_simple-1.1.jar',
                    'SBusJavaFacade.jar',
                    'SCommon.jar',
                    'SDaemon.jar',
                    '']
        jar_deps = [os.path.join(str_prfx, x) for x in jar_deps]
        str_dmn_clspth = ':'.join(jar_deps) + ':' + storlet_path

        self.logger.debug('START_DAEMON: daemon lang = %s' % daemon_language)
        self.logger.debug('START_DAEMON: str_dmn_clspth = %s' % str_dmn_clspth)
        self.logger.debug('START_DAEMON: storlet_name = %s' % storlet_name)
        self.logger.debug('START_DAEMON: pool_size = %d' % pool_size)
        self.logger.debug('START_DAEMON: uds_path = %s' % uds_path)
        self.logger.debug('START_DAEMON: log_level = %s' % log_level)

        str_daemon_main_class = "com.ibm.storlet.daemon.SDaemon"

        self.logger.debug('START_DAEMON:preparing arguments')
        if os.environ.get('CLASSPATH'):
            str_dmn_clspth = os.environ['CLASSPATH'] + ':' + str_dmn_clspth
        if os.environ.get('LD_LIBRARY_PATH'):
            str_library_path = os.environ['LD_LIBRARY_PATH'] + ':' + str_prfx
        else:
            str_library_path = str_prfx

        env = dict()
        env['CLASSPATH'] = str_dmn_clspth
        env['LD_LIBRARY_PATH'] = str_library_path

        pargs = ['/usr/bin/java', str_daemon_main_class, storlet_name,
                 uds_path, log_level, str(pool_size), container_id]
        str_pargs = ' '.join(pargs)
        self.logger.debug('START_DAEMON: pargs = %s' % str_pargs)

        return pargs, env

    def spawn_subprocess(self, pargs, env):
        """
        Launch a JVM process for some storlet daemon

        :param pargs: Arguments for the JVM
        :param env: Environment value
        :returns: (Status, Description text of possible error)
        """
        b_status = True
        error_text = ''
        try:
            self.logger.debug('START_DAEMON: actual invocation')
            self.logger.debug('The arguments are: {0}'.format(str(pargs)))
            # TODO(takashi): We had better use contextmanager
            # TODO(takashi): Where is this closed?
            # TODO(takashi): Should we really use this?
            dn = open('/dev/null', 'w')
            daemon_p = subprocess.Popen(pargs,
                                        stdout=dn,
                                        stderr=subprocess.PIPE,
                                        shell=False,
                                        env=env)

            logger_p = subprocess.Popen('logger',
                                        stdin=daemon_p.stderr,
                                        stdout=dn,
                                        stderr=dn,
                                        shell=False)
            jvm_pid = daemon_p.pid
            # Wait for the JVM initializes itself
            time.sleep(1)
            self.logger.debug('Daemon process ID is: {0}'.format(jvm_pid))
            self.logger.debug('Logger process ID is: {0}'.format(logger_p.pid))
            storlet_name = pargs[2]

            # Does JVM run?
            b_status, error_text = self.get_process_status_by_pid(
                jvm_pid, storlet_name)
            if b_status:
                self.logger.debug('Keeping JVM PID in' +
                                  'storlet_name_to_pid[{0}] = {1}'.
                                  format(storlet_name, jvm_pid))
                # Keep JVM PID
                self.storlet_name_to_pid[storlet_name] = jvm_pid
                if not self.wait_for_daemon_to_initialize(storlet_name):
                    # TODO(takashi): We shoud use more specific exception
                    raise Exception('No response from Daemon')
            self.logger.debug('START_DAEMON: just occurred')
            error_text = 'OK'
        except Exception:
            b_status = False
            error_text = 'Failed to start subprocess %s' % str(pargs)
            self.logger.exception(error_text)

        # TODO(takashi): Now we return error text in tuple, but I think we had
        #                better make this raise Exception including message
        return b_status, error_text

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
        read_fd, write_fd = os.pipe()
        try:
            dtg = ClientSBusOutDatagram.create_service_datagram(
                SBUS_CMD_PING, write_fd)
            for i in range(self.NUM_OF_TRIES_PINGING_STARTING_DAEMON):
                ret = SBus.send(storlet_pipe_name, dtg)
                if ret >= 0:
                    if os.read(read_fd, 128) == 'OK':
                        return True
                    time.sleep(1)
            else:
                return False
        finally:
            os.close(read_fd)
            os.close(write_fd)

    def process_start_daemon(self, daemon_language, storlet_path, storlet_name,
                             pool_size, uds_path, log_level, container_id):
        """
        Start storlet daemon process

        :param daemon_language: Language the storlet is written on.
                                Now (01-Dec-2014) only Java is supported.
        :param storlet_path: Path to the folder where storlet JRE file is
        :param storlet_name: Storlet main class name
        :param pool_size: Number of threads that storlet daemon's thread
                          pool provides
        :param uds_path: Path to pipe daemon is going to listen to
        :param log_level: Logger verbosity level
        :param container_id: container id

        :returns: (Status, Description text of possible error)
        """
        if daemon_language.lower() in ['java']:
            pargs, env = self.get_jvm_args(
                daemon_language, storlet_path, storlet_name,
                pool_size, uds_path, log_level, container_id)
        else:
            error_txt = 'Got unsupported daemon language: %s' % daemon_language
            self.logger.error(error_txt)
            return False, error_txt

        self.logger.debug('Assigning storlet_name_to_pipe_name[{0}]={1}'.
                          format(storlet_name, uds_path))
        self.storlet_name_to_pipe_name[storlet_name] = uds_path

        self.logger.debug('Validating that {0} is not already running'.
                          format(storlet_name))
        b_status, _ = self.get_process_status_by_name(storlet_name)
        if b_status:
            error_text = '{0} is already running'.format(storlet_name)
            self.logger.debug(error_text)
        else:
            self.logger.debug('{0} is not running. About to spawn process'.
                              format(storlet_name))
            b_status, error_text = self.spawn_subprocess(pargs, env)

        return b_status, error_text

    def get_process_status_by_name(self, storlet_name):
        """
        Check if the daemon runs for the specific storlet

        :param storlet_name: Storlet name we are checking the daemon for
        :returns: (Status, Description text of possible error)
        """
        self.logger.debug('Current storlet name is: {0}'.format(storlet_name))
        self.logger.debug('storlet_name_to_pid has {0}'.
                          format(str(self.storlet_name_to_pid.keys())))
        b_status = False
        error_text = ''
        self.logger.debug('Checking status for storlet {0}'.
                          format(storlet_name))
        daemon_pid = self.storlet_name_to_pid.get(storlet_name, -1)
        if -1 != daemon_pid:
            b_status, error_text = self.get_process_status_by_pid(
                daemon_pid, storlet_name)
        else:
            error_text = 'Storlet name {0} not found in map'. \
                         format(storlet_name)
            self.logger.debug(error_text)

        return b_status, error_text

    def get_process_status_by_pid(self, daemon_pid, storlet_name):
        """
        Check if a process with specific ID runs

        :param daemon_pid:   Storlet daemon process ID
        :param storlet_name: Storlet name we are checking the daemon for
        :returns: (Status, Description text of possible error)
        """
        b_status = False
        error_text = ''
        obtained_pid = 0
        obtained_code = 0
        try:
            obtained_pid, obtained_code = os.waitpid(daemon_pid, os.WNOHANG)
            error_text = 'Storlet {0}, PID = {1}, ErrCode = {2}'. \
                         format(storlet_name, obtained_pid, obtained_code)
            self.logger.debug(error_text)
        except OSError as err:
            if err.errno == errno.ESRCH:
                error_text = 'No running daemon for {0}'.format(storlet_name)
            elif err.errno == errno.EPERM:
                error_text = 'No permission to access daemon for {0}'. \
                    format(storlet_name)
            else:
                error_text = 'Unknown error'
        else:
            if 0 == obtained_pid and 0 == obtained_code:
                error_text = 'Storlet {0} seems to be OK'.format(storlet_name)
                b_status = True
            else:
                error_text = 'Storlet {0} is terminated'.format(storlet_name)
            self.logger.debug(error_text)
        return b_status, error_text

    def process_kill(self, storlet_name):
        """
        Kill the storlet daemon immediately
        (kill -9 $DMN_PID)

        :param storlet_name: Storlet name we are checking the daemon for
        :returns: (Status, Description text of possible error)
        """
        self.logger.debug('Current storlet name is: {0}'.format(storlet_name))
        b_success = True
        error_text = ''
        dmn_pid = self.storlet_name_to_pid.get(storlet_name, -1)
        self.logger.debug('Daemon PID is: {0}'.format(dmn_pid))
        if -1 != dmn_pid:
            try:
                os.kill(dmn_pid, signal.SIGKILL)
                obtained_pid, obtained_code = os.waitpid(dmn_pid, os.WNOHANG)
                error_text = 'Storlet {0}, PID = {1}, ErrCode = {2}'. \
                             format(storlet_name, obtained_pid, obtained_code)
                self.logger.debug(error_text)
            except Exception:
                self.logger.debug('Crash while killing storlet')
            self.storlet_name_to_pid.pop(storlet_name)
        else:
            error_text = '{0} is not found'.format(storlet_name)
            b_success = False

        return b_success, error_text

    def process_kill_all(self):
        """
        Kill every one.

        :returns: (Status (True),
                   Description text of possible error ('OK'))
        """
        for storlet_name in self.storlet_name_to_pid.keys():
            self.process_kill(storlet_name)
        # TODO(takashi): Can we really always return True?
        return True, 'OK'

    def shutdown_all_processes(self):
        """
        send HALT command to every spawned process

        :returns: (Status, Termination message)
        """
        answer = ''
        for storlet_name in self.storlet_name_to_pid.keys():
            self.shutdown_process(storlet_name)
            answer += storlet_name + ': terminated; '
        self.logger.info('All the processes terminated')
        self.logger.info(answer)
        # TODO(takashi): Can we really always return True?
        return True, answer

    def shutdown_process(self, storlet_name):
        """
        send HALT command to storlet daemon

        :param storlet_name: Storlet name we are checking the daemon for
        :returns: Status
        """
        b_status = False
        self.logger.debug('Inside shutdown_process {0}'.format(storlet_name))
        storlet_pipe_name = self.storlet_name_to_pipe_name[storlet_name]
        self.logger.debug('Send HALT command to {0} via {1}'.
                          format(storlet_name, storlet_pipe_name))
        # TODO(takashi): We had better use contextmanager
        read_fd, write_fd = os.pipe()
        dtg = ClientSBusOutDatagram.create_service_datagram(
            SBUS_CMD_HALT,
            write_fd)
        SBus.send(storlet_pipe_name, dtg)
        os.close(read_fd)
        os.close(write_fd)
        dmn_pid = self.storlet_name_to_pid.get(storlet_name, -1)
        self.logger.debug('Storlet Daemon PID is {0}'.format(dmn_pid))
        if -1 != dmn_pid:
            os.waitpid(dmn_pid, 0)
            self.storlet_name_to_pid.pop(storlet_name)
            b_status = True
        return b_status

    @command_handler
    def start_daemon(self, container_id, prms):
        b_status, error_text = self.process_start_daemon(
            prms['daemon_language'],
            prms['storlet_path'],
            prms['storlet_name'],
            prms['pool_size'],
            prms['uds_path'],
            prms['log_level'],
            container_id)
        return CommandResponse(b_status, error_text, True)

    @command_handler
    def stop_daemon(self, container_id, prms):
        b_status, error_text = self.process_kill(prms['storlet_name'])
        return CommandResponse(b_status, error_text, True)

    @command_handler
    def daemon_status(self, container_id, prms):
        b_status, error_text = \
            self.get_process_status_by_name(prms['storlet_name'])
        return CommandResponse(b_status, error_text, True)

    @command_handler
    def stop_daemons(self, container_id, prms):
        b_status, error_text = self.process_kill_all()
        return CommandResponse(b_status, error_text, False)

    @command_handler
    def halt(self, container_id, prms):
        b_status, error_text = self.shutdown_all_processes()
        return CommandResponse(b_status, error_text, False)

    @command_handler
    def ping(self, container_id, prms):
        return CommandSuccess('OK')

    def get_handler(self, command):
        """
        Decide handler function correspoiding to the recieved command

        :param command: command
        :returns: handler function
        """
        if not command.startswith(SBUS_CMD_PREFIX):
            raise ValueError('got unknown command %s' % command)
        func_name = command[len(SBUS_CMD_PREFIX):].lower()
        try:
            handler = getattr(self, func_name)
            getattr(handler, 'is_command_handler')
        except AttributeError:
            raise ValueError('got unknown command %s' % command)
        return handler

    def dispatch_command(self, dtg, container_id):
        """
        Parse datagram. React on the request.

        :param dtg: Datagram to process
        :param container_id: container id

        :returns: CommandResponse instance
        """
        command = dtg.command
        prms = dtg.params
        self.logger.debug("Received command {0}".format(command))

        try:
            handler = self.get_handler(command)
        except ValueError as e:
            self.logger.exception('Failed to decide handler')
            return CommandFailure(str(e))
        else:
            self.logger.debug('Do %s' % command)
            return handler(container_id, prms)
        finally:
            self.logger.debug('Done')

    def main_loop(self, container_id):
        """
        The 'internal' loop. Listen to SBus, receive datagram,
        dispatch command, report back.

        :param container_id: container id
        :returns: exit status (SUCCESS/FAILURE)
        """

        # Create SBus. Listen and process requests
        sbus = SBus()
        fd = sbus.create(self.pipe_path)
        if fd < 0:
            self.logger.error("Failed to create SBus. exiting.")
            return EXIT_FAILURE

        while True:
            rc = sbus.listen(fd)
            if rc < 0:
                self.logger.error("Failed to wait on SBus. exiting.")
                return EXIT_FAILURE
            self.logger.debug("Wait returned")

            dtg = sbus.receive(fd)
            # TODO(eranr):
            # Should we really be exitting here.
            # If so should we exit the container altogether, so
            # that it gets restarted?
            if dtg is None:
                self.logger.error("Failed to receive message. Exitting.")
                return EXIT_FAILURE

            outfd = dtg.service_out_fd
            if outfd is None:
                self.logger.error("Received message does not have outfd."
                                  " continuing.")
                continue

            self.logger.debug("Received outfd %d" % outfd)
            with os.fdopen(outfd, 'w') as outfile:
                resp = self.dispatch_command(dtg, container_id)
                self.log_and_report(outfile, resp)
                if not resp.iterable:
                    break

        # We left the main loop for some reason. Terminating.
        self.logger.debug('Leaving main loop')
        return EXIT_SUCCESS

    def log_and_report(self, outfile, resp):
        """
        Send result result description message back to swift middleware

        :param outfile : Output channel to send the message to
        :param resp: CommandResponse instance
        """
        answer = resp.report_message
        self.logger.debug(' Just processed command')
        self.logger.debug(' Going to answer: %s' % answer)
        try:
            outfile.write(answer)
            self.logger.debug(" ... and still alive")
        except Exception:
            self.logger.debug('Problem while writing response %s' % answer)


def start_logger(logger_name, log_level, container_id):
    """

    Initialize logging of this process and set logger format

    :param logger_name: The name to report with
    :param log_level: The verbosity level. This should be selected
    :param container_id: container id
    """
    logging.raiseExceptions = False
    log_level = log_level.upper()

    # NOTE(takashi): currently logging.WARNING is defined as the same value
    #                as logging.WARN, so we can properly handle WARNING here
    try:
        level = getattr(logging, log_level)
    except AttributeError:
        level = logging.ERROR

    logger = logging.getLogger("CONT #" + container_id + ": " + logger_name)

    if log_level == 'OFF':
        logging.disable(logging.CRITICAL)
    else:
        logger.setLevel(level)

    log_handler = SysLogHandler('/dev/log')
    str_format = '%(name)-12s: %(levelname)-8s %(funcName)s' + \
                 ' %(lineno)s [%(process)d, %(threadName)s]' + \
                 ' %(message)s'
    formatter = logging.Formatter(str_format)
    log_handler.setFormatter(formatter)
    log_handler.setLevel(level)
    logger.addHandler(log_handler)
    return logger


def usage():
    """
    Print the expected command line arguments.
    """
    print("daemon_factory <path> <log level> <container_id>")


def main(argv):
    """
    The entry point of daemon_factory process

    :param argv: parameters given from command line
    """
    if (len(argv) != 3):
        usage()
        # TODO(takashi): returning non-zero value is better?
        return EXIT_FAILURE

    pipe_path = argv[0]
    log_level = argv[1]
    container_id = argv[2]

    # Initialize logger
    logger = start_logger("daemon_factory", log_level, container_id)
    logger.debug("Daemon factory started")
    SBus.start_logger("DEBUG", container_id=container_id)

    # Impersonate the swift user
    pw = pwd.getpwnam('swift')
    os.setresgid(pw.pw_gid, pw.pw_gid, pw.pw_gid)
    os.setresuid(pw.pw_uid, pw.pw_uid, pw.pw_uid)

    # create an instance of daemon_factory
    factory = DaemonFactory(pipe_path, logger)

    # Start the main loop
    return factory.main_loop(container_id)
