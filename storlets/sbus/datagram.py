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

from storlets.sbus import file_description as sbus_fd


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
    The manager class for the datagram passed over sbus protocol
    """

    def __init__(self, command, fds, metadata, params=None, task_id=None):
        """
        Create SBusDatagram instance

        :param command: A string encoding the command to send
        :param fds: A list of file descriptors (integer) to pass with
                    the command
        :param md: A list of dictionaries, where the i'th dictionary is the
                   metadata of the i'th fd.
        :param params: A optional dictionary with parameters for the command
                       execution
        :param task_id: An optional string task id. This is currently used for
                        cancel command
        """
        self.command = command
        if len(fds) != len(metadata):
            raise ValueError('Length mismatch fds:%s metadata:%s' %
                             (len(fds), len(metadata)))
        self.fds = fds
        self.metadata = metadata
        self.params = params
        self.task_id = task_id

    @classmethod
    def create_service_datagram(cls, command, outfd, params=None,
                                task_id=None):
        """
        Create datagram which only has one service out fd

        This method is used to create datagram for some command type, which
        only needs one service out fd. Currently we can use this function for
        the following commands.
         - SBUS_CMD_HALT
         - SBUS_CMD_START_DAEMON
         - SBUS_CMD_STOP_DAEMON
         - SBUS_CMD_DAEMON_STATUS
         - SBUS_CMD_STOP_DAEMONS
         - SBUS_CMD_PING
         - SBUS_CMD_CANCEL

        :param command: command type
        :param outfd: service out fd integer
        :param params: A optional dictionary with parameters for the command
                       execution
        :param task_id: An optional string task id
        """
        # TODO(takashi): Maybe we can get rid of this function
        md = [FDMetadata(sbus_fd.SBUS_FD_SERVICE_OUT).to_dict()]
        fds = [outfd]
        return cls(command, fds, md, params, task_id)

    @classmethod
    def build_from_raw_message(cls, fds, str_md, str_cmd_params):
        """
        Build SBusDatagram from raw message recieved over sbus

        :param fds: A list of file descriptors (integer) to pass with
                    the command
        :param str_md: json serialized metadata dict
        :param str_cmd_params: json serialized command parameters dict
        """
        metadata = json.loads(str_md)
        cmd_params = json.loads(str_cmd_params)
        command = cmd_params.get('command')
        params = cmd_params.get('params')
        task_id = cmd_params.get('task_id')
        return cls(command, fds, metadata, params, task_id)

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

    @property
    def serialized_cmd_params(self):
        return json.dumps(self.cmd_params)

    @property
    def serialized_metadata(self):
        return json.dumps(self.metadata)

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

    def _find_fds(self, fdtype):
        """
        Get a list of file descriptors for the given fd type

        :param fdtype: file descriptor type
        :returns: a list of file descriptors
        """
        ret = []
        for i in xrange(len(self.metadata)):
            if self.metadata[i]['storlets']['type'] == fdtype:
                ret.append(self.fds[i])
        return ret

    def _find_fd(self, fdtype):
        """
        Get a single file descriptor for the given fd type

        :param fdtype: file descriptor type
        :returns: one file descriptor (integer)
        """
        ret = self._find_fds(fdtype)
        if not ret:
            return None
        else:
            # TODO(takashi): we should raise error if we get multiple fds
            #                for given type. This is to be done when we add
            #                fd validation.
            return ret[0]

    def __str__(self):
        return 'num_fds=%s, md=%s, cmd_params=%s' % (
            self.num_fds,
            str(self.serialized_metadata),
            str(self.serialized_cmd_params))
