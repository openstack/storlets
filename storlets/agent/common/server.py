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
from functools import partial
import json
import os
import signal

from storlets.sbus import SBus
import storlets.sbus.command as sbus_cmd

EXIT_SUCCESS = 0
EXIT_FAILURE = 1

LOOP_TIMEOUT = 0.5
LISTEN_TIMEOUT = 300


class CommandResponse(Exception):
    """
    The result of command execution
    """

    def __init__(self, status, message, iterable=True, task_id=None):
        """
        Construct CommandResponse instance

        :param status: task status
        :param message: message to be returned and logged
        :param iterable: whether we can keep SDaemon process running
        :param task_id: ID assigned to the requested task
        """
        self.status = status
        self.message = message

        # NOTE(takashi): iterable controls whether the server main loop should
        #                exit or not as a result of processing the command
        self.iterable = iterable

        self.task_id = task_id

    @property
    def report_message(self):
        rsp = {'status': self.status, 'message': self.message}
        if self.task_id:
            rsp['task_id'] = self.task_id
        return json.dumps(rsp)


CommandSuccess = partial(CommandResponse, True)
CommandFailure = partial(CommandResponse, False)


def command_handler(func):
    """
    Decorator for handler methods called according to given sbus command
    """
    func.is_command_handler = True
    return func


class SBusServer(object):
    """
    Basic implementation for server processes listening on sbus protocol

    NOTE(takash): we should implement some termination functions like
                  _terminate and halt, otherwise they raise
                  NotImplementedError.
    """
    def __init__(self, sbus_path, logger):
        self.sbus_path = sbus_path
        self.logger = logger
        self.running = True
        self.listen_timeout = LISTEN_TIMEOUT
        self.loop_timeout = LOOP_TIMEOUT

    def get_handler(self, command):
        """
        Decide handler function corresponding to the received command

        :param command: command
        :returns: handler function
        """
        # All commands should be defined in storlets.sbus.command
        if not hasattr(sbus_cmd, command):
            raise ValueError('Unknown command %s' % command)

        func_name = command[len(sbus_cmd.SBUS_CMD_PREFIX):].lower()
        try:
            handler = getattr(self, func_name)
            getattr(handler, 'is_command_handler')
        except AttributeError:
            raise ValueError('Command %s is not allowed for this server' %
                             command)
        return handler

    def dispatch_command(self, dtg):
        """
        Parse datagram. React on the request.

        :param dtg: Datagram received from client

        :returns: True if the server can continue its main loop
                  False if the server should terminate its main loop
        """
        command = dtg.command
        self.logger.debug("Received command %s" % command)

        try:
            handler = self.get_handler(command)
            resp = handler(dtg)
        except ValueError as err:
            self.logger.exception('Failed to handle request')
            resp = CommandFailure(str(err))
        except CommandResponse as err:
            resp = err
        except Exception:
            self.logger.exception('Failed to handle request')
            resp = CommandFailure('Internal error')

        self.logger.info('Command:%s Response:%s' %
                         (command, resp.report_message))

        outfd = dtg.service_out_fd
        with os.fdopen(outfd, 'wb') as outfile:
            self._respond(outfile, resp)

        return resp.iterable

    def _respond(self, outfile, resp):
        """
        Send result description message back to gateway

        :param outfile : Output channel to send the message to
        :param resp: CommandResponse instance
        """
        try:
            outfile.write(resp.report_message.encode('utf-8'))
        except IOError:
            self.logger.exception('Unable to return response to client')

    @command_handler
    def ping(self, dtg):
        self.logger.debug('Received ping. Responding')
        return CommandSuccess('OK')

    @command_handler
    def halt(self, dtg):
        raise NotImplementedError()

    def _terminate(self):
        raise NotImplementedError()

    def _force_terminate(self):
        raise NotImplementedError()

    def _graceful_shutdown(self, *args):
        self.logger.info("received SIGHUP. Shutting down gracefully")
        self.running = False

    def _force_shutdown(self, *args):
        self.logger.info("received SIGTERM. Shutting down now")
        try:
            self._force_terminate()
        except Exception:
            self.logger.exception(
                "Failed to force_terminate. The process stops anyway")
        finally:
            os._exit(1)

    def main_loop(self):
        """
        Main loop to run storlet application

        :returns: EXIT_SUCCESS when the loop exists normally
                  EXIT_FAILURE when an error occurs in main loop
        """
        sbus = SBus()
        fd = sbus.create(self.sbus_path)
        if fd < 0:
            self.logger.error("Failed to create SBus. exiting.")
            return EXIT_FAILURE

        signal.signal(signal.SIGHUP, self._graceful_shutdown)
        signal.signal(signal.SIGTERM, self._force_shutdown)

        loop_cnt = 0
        status = EXIT_SUCCESS

        while self.running:
            rc = sbus.listen(fd, self.loop_timeout)

            if rc < 0:
                self.logger.error("Failed to wait on SBus. exiting.")
                status = EXIT_FAILURE
                break
            elif rc == 0:
                loop_cnt += 1
                if loop_cnt * self.loop_timeout >= self.listen_timeout:
                    self.logger.debug("Timed out while listening. exiting.")
                    break
                continue

            # Reset loop_cnt here as a request comes via sbus
            loop_cnt = 0

            dtg = sbus.receive(fd)
            if dtg is None:
                self.logger.error("Failed to receive message. exiting")
                status = EXIT_FAILURE
                break

            if not self.dispatch_command(dtg):
                break

        self.logger.debug('Leaving main loop')
        self._terminate()

        return status
