# Copyright (c) 2016 OpenStack Foundation.
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
import json
import os
from storlets.sbus import SBus
from storlets.sbus import command as sbus_cmd
from storlets.sbus.datagram import SBusFileDescriptor, build_datagram
from storlets.sbus.file_description import SBUS_FD_SERVICE_OUT
from storlets.sbus.client.exceptions import SBusClientIOError, \
    SBusClientMalformedResponse, SBusClientSendError


class SBusResponse(object):
    def __init__(self, status, message, task_id=None):
        """
        Construct SBusResponse class

        :param status: Whether the server succeed to process the given request
        :param message: Messages to describe the process result
        :param task_id: Id assigned to each tasks
        """
        self.status = status
        self.message = message
        self.task_id = task_id


class SBusClient(object):
    def __init__(self, socket_path, chunk_size=16):
        self.socket_path = socket_path
        self.chunk_size = chunk_size

    def _parse_response(self, str_response):
        """
        Parse response string received from container side

        :param str_response: response string
        :returns: SBusResponse instance
        """
        try:
            resp = json.loads(str_response)
            status = resp['status']
            message = resp['message']
        except (ValueError, KeyError):
            raise SBusClientMalformedResponse('Got malformed response')

        # NOTE(takashi): task_id is currently used only in EXECUTE command, so
        #                we don't fail here even if the given response doesn't
        #                have task_id.
        task_id = resp.get('task_id')

        return SBusResponse(status, message, task_id)

    def _request(self, command, params=None, task_id=None, extra_fds=None):
        read_fd, write_fd = os.pipe()
        try:
            try:
                sfds = \
                    [SBusFileDescriptor(SBUS_FD_SERVICE_OUT, write_fd)] + \
                    (extra_fds or [])
                datagram = build_datagram(command, sfds, params, task_id)
                rc = SBus.send(self.socket_path, datagram)
                if rc < 0:
                    raise SBusClientSendError(
                        'Faild to send command(%s) to socket %s' %
                        (datagram.command, self.socket_path))
            finally:
                # We already sent the write fd to remote, so should close it
                # in local side before reading response
                os.close(write_fd)

            reply = b''
            while True:
                try:
                    buf = os.read(read_fd, self.chunk_size)
                except IOError:
                    raise SBusClientIOError(
                        'Failed to read data from read pipe')
                if not buf:
                    break
                reply = reply + buf
        finally:
            os.close(read_fd)

        return self._parse_response(reply.decode('utf-8'))

    def execute(self, invocation_params, invocation_fds):
        return self._request(sbus_cmd.SBUS_CMD_EXECUTE,
                             params=invocation_params,
                             extra_fds=invocation_fds)

    def ping(self):
        return self._request(sbus_cmd.SBUS_CMD_PING)

    def start_daemon(self, language, storlet_path, storlet_id,
                     uds_path, log_level, pool_size,
                     language_version):
        params = {'daemon_language': language, 'storlet_path': storlet_path,
                  'storlet_name': storlet_id, 'uds_path': uds_path,
                  'log_level': log_level, 'pool_size': pool_size}
        if language_version:
            params['daemon_language_version'] = language_version

        return self._request(sbus_cmd.SBUS_CMD_START_DAEMON, params)

    def stop_daemon(self, storlet_name):
        return self._request(sbus_cmd.SBUS_CMD_STOP_DAEMON,
                             {'storlet_name': storlet_name})

    def stop_daemons(self):
        return self._request(sbus_cmd.SBUS_CMD_STOP_DAEMONS)

    def halt(self):
        return self._request(sbus_cmd.SBUS_CMD_HALT)

    def daemon_status(self, storlet_name):
        return self._request(sbus_cmd.SBUS_CMD_DAEMON_STATUS,
                             {'storlet_name': storlet_name})

    def cancel(self, task_id):
        return self._request(sbus_cmd.SBUS_CMD_CANCEL, task_id=task_id)
