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
import copy
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

import sbus.file_description as sbus_fd


class FDMetadata(object):
    def __init__(self, fdtype, storlets_metadata=None, storage_metadata=None):
        self.fdtype = fdtype
        self.storlets_metadata = storlets_metadata or {}
        self.storage_metadata = storage_metadata or {}

    def to_dict(self):
        storlets_metadata = copy.deepcopy(self.storlets_metadata)
        storlets_metadata['type'] = self.fdtype
        return {'storlets': storlets_metadata,
                'storage': self.storage_metadata}

    @classmethod
    def from_dict(cls, metadict):
        _metadict = copy.deepcopy(metadict)
        storlets_metadata = _metadict['storlets']
        storage_metadata = _metadict['storage']
        fdtype = storlets_metadata.pop('type')
        return cls(fdtype, storlets_metadata, storage_metadata)


class SBusDatagram(object):
    """
    Basic class for all SBus datagrams
    """
    def __init__(self, command, fds, metadata, params=None, task_id=None):
        self.command = command
        if len(fds) != len(metadata):
            raise ValueError('Length mismatch fds:%s metadata:%s' %
                             (len(fds), len(metadata)))
        self.fds = fds
        self.metadata = metadata
        self.params = params
        self.task_id = task_id

    @property
    def num_fds(self):
        return len(self.fds)

    @property
    def cmd_params(self):
        cmd_params = {'command': self.command}
        if self.params:
            cmd_params['params'] = self.params
        if self.task_id:
            cmd_params['task_id'] = self.task_id
        return cmd_params


class ClientSBusOutDatagram(SBusDatagram):
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
        :param params: A optional dictionary with parameters for the command
                       execution
        :param task_id: An optional string task id

        """
        super(ClientSBusOutDatagram, self).__init__(
            command, fds, md, params, task_id)

    @staticmethod
    def create_service_datagram(command, outfd, params=None, task_id=None):
        md = [FDMetadata(sbus_fd.SBUS_FD_SERVICE_OUT).to_dict()]
        fds = [outfd]
        return ClientSBusOutDatagram(command, fds, md, params, task_id)

    @property
    def serialized_cmd_params(self):
        return json.dumps(self.cmd_params)

    @property
    def serialized_metadata(self):
        return json.dumps(self.metadata)

    def __str__(self):
        return 'num_fds=%s, md=%s, cmd_params=%s' % (
            self.num_fds,
            str(self.serialized_metadata),
            str(self.serialized_cmd_params))


class ServerSBusInDatagram(SBusDatagram):
    """De-Serializes a command coming form the wire.

    The incoming message is serilized by the ClinetSBusOutDatagram.
    The message structure is illustrated in
    SBusJavaFacade.ServerSBusInDatagram.
    SBusJavaFacade.ServerSBusInDatagram is the Java equivalent, having the
    same parameters.

    """
    def __init__(self, fds, str_md, str_cmd_params):
        """
        :param fds: An array of file descriptors to pass with the command
        :param str_md: serialized metadata
        :param str_cmd_params: serialized command parameters
        """
        md = json.loads(str_md)
        cmd_params = json.loads(str_cmd_params)
        command = cmd_params.get('command')
        params = cmd_params.get('params')
        task_id = cmd_params.get('task_id')
        super(ServerSBusInDatagram, self).__init__(
            command, fds, md, params, task_id)

    def _find_fds(self, fdtype):
        ret = []
        for i in xrange(len(self.metadata)):
            if self.metadata[i]['storlets']['type'] == fdtype:
                ret.append(self.fds[i])
        return ret

    def _find_fd(self, fdtype):
        ret = self._find_fds(fdtype)
        if not ret:
            return None
        else:
            return ret[0]

    @property
    def service_out_fd(self):
        return self._find_fd(sbus_fd.SBUS_FD_SERVICE_OUT)

    @property
    def object_out_fds(self):
        return self._find_fds(sbus_fd.SBUS_FD_OUTPUT_OBJECT)

    @property
    def object_metadata_out_fds(self):
        return self._find_fds(sbus_fd.SBUS_FD_OUTPUT_OBJECT_METADATA)

    @property
    def task_id_out_fd(self):
        return self._find_fd(sbus_fd.SBUS_FD_OUTPUT_TASK_ID)

    @property
    def logger_out_fd(self):
        return self._find_fd(sbus_fd.SBUS_FD_LOGGER)

    @property
    def object_in_fds(self):
        return self._find_fds(sbus_fd.SBUS_FD_INPUT_OBJECT)

    @property
    def object_in_metadata(self):
        return [md['storage'] for md in self.metadata
                if md['storlets']['type'] == sbus_fd.SBUS_FD_INPUT_OBJECT]

    @property
    def object_in_storlet_metadata(self):
        return [md['storlets'] for md in self.metadata
                if md['storlets']['type'] == sbus_fd.SBUS_FD_INPUT_OBJECT]


# Curerrently we have no Server to Client commands
# This serves as a place holder should we want to bring the
# function back:
# In the past this was used for a allowing a storlet
# to create new objects via a PUT on container
# with X-Run-Storlet.
class ClientSBusInDatagram(object):
    def __init__(self):
        raise NotImplementedError
