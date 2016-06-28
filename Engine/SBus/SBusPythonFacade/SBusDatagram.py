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

import json

# Designating the host side as the client side and the storlet side
# as the server side, the IPC between the client and server requires
# 4 different serialization / de-serialization objects:
# 1. Serializing client commands (client side)
# 2. De-srializing client commands (server side)
# 3. Serializing server response (server side)
# 4. De-srializing server response (client side)
# This python module implements the client side objects as follows:
# ClientSBusOutDatagram - Serializing client commands
# ServerSBusInDatagram - De-serializing client commands
# ClientSBusInDatagram - De-srializing server response

from SBusFileDescription import SBUS_FD_SERVICE_OUT


class ClientSBusOutDatagram(object):
    """Serializes a command to be sent on the wire.

    The outgoing message is parsed by the ServerSBusInDatagram.
    The message structure is illustrated in
    SBusJavaFacade.ServerSBusInDatagram.
    Once constructed, there are accessors for the serilized data.

    """

    def __init__(self, command, fds, md, params=None, task_id=None):
        """ Constructs ClientSBusOutDatagram

        :param command: A string encoding the command to send
        :param fds: An array of file descriptors to pass with the command
        :param md: An array of dictionaries, where the i'th dictionary is the
                   metadata of the i'th fd.
        :params: A optional dictionary with parameters for the command
                 execution
        :params: An optional string task id

        """
        self._command = command
        self._fds = fds
        self._md = md
        self._params = params
        self._task_id = task_id

    @staticmethod
    def create_service_datagram(command, outfd, params=None, task_id=None):
        md = [{'storlets': {'type': SBUS_FD_SERVICE_OUT},
              'storage': {}}]
        fds = [outfd]
        return ClientSBusOutDatagram(command, fds, md, params, task_id)

    def _get_num_fds(self):
        return len(self._fds)
    num_fds = property(_get_num_fds, None)

    def _get_fds(self):
        return self._fds
    fds = property(_get_fds, None)

    @property
    def serialized_cmd_params(self):
        res = {}
        res['command'] = self._command
        if self._params:
            res['params'] = self._params
        if self._task_id:
            res['task_id'] = self._task_id
        return json.dumps(res)

    @property
    def serialized_md(self):
        return json.dumps(self._md)

    def __str__(self):
        return 'num_fds=%s, md=%s, cmd_params=%s' % (
            self.num_fds,
            str(self.serialized_md),
            str(self.serialized_cmd_params))


class ServerSBusInDatagram(object):
    """De-Serializes a command coming form the wire.

    The incoming message is serilized by the ClinetSBusOutDatagram.
    The message structure is illustrated in
    SBusJavaFacade.ServerSBusInDatagram.
    SBusJavaFacade.ServerSBusInDatagram is the Java equivalent, having the
    same parameters.

    """
    def __init__(self, fds, str_md, str_params):
        self._fds = fds
        self._md = json.loads(str_md)
        cmd_params = json.loads(str_params)
        self._command = cmd_params.get('command')
        self._params = cmd_params.get('params')
        self._task_id = cmd_params.get('task_id')

    def _get_fds(self):
        return self._fds
    fds = property(_get_fds, None)

    def _get_num_fds(self):
        return len(self._fds)
    num_fds = property(_get_num_fds, None)

    def _get_command(self):
        return self._command
    command = property(_get_command, None)

    def _get_md(self):
        return self._md
    metadata = property(_get_md, None)

    def _get_params(self):
        return self._params
    params = property(_get_params, None)

    def _get_task_id(self):
        return self._task_id
    task_id = property(_get_task_id, None)

    def get_service_out_fd(self):
        for i in xrange(len(self._md)):
            if self._md[i]['storlets']['type'] == SBUS_FD_SERVICE_OUT:
                return self._fds[i]
        return None


# Curerrently we have no Server to Client commands
# This serves as a place holder should we want to bring the
# function back:
# In the past this was used for a allowing a storlet
# to create new objects via a PUT on container
# with X-Run-Storlet.
class ClientSBusInDatagram(object):
    def __init__(self):
        raise NotImplementedError
