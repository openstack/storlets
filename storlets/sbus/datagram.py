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
import abc
import copy
import json

from storlets.sbus import command as sbus_cmd
from storlets.sbus import file_description as sbus_fd


class SBusFileDescriptor(object):
    """
    The management class for the file descriptor information
    """

    def __init__(self, fdtype, fileno, storlets_metadata=None,
                 storage_metadata=None):
        self.fdtype = fdtype
        self.fileno = fileno
        self.storlets_metadata = storlets_metadata or {}
        self.storage_metadata = storage_metadata or {}

    @property
    def metadata(self):
        storlets_metadata = copy.deepcopy(self.storlets_metadata)
        storlets_metadata['type'] = self.fdtype
        return {'storlets': storlets_metadata,
                'storage': self.storage_metadata}

    @classmethod
    def from_fileno_and_metadata_dict(cls, fileno, metadict):
        _metadict = copy.deepcopy(metadict)
        storlets_metadata = _metadict['storlets']
        storage_metadata = _metadict['storage']
        fdtype = storlets_metadata.pop('type')
        return cls(fdtype, fileno, storlets_metadata, storage_metadata)


class SBusDatagram(object, metaclass=abc.ABCMeta):
    """
    The manager class for the datagram passed over sbus protocol
    """

    @property
    @abc.abstractmethod
    def _required_fdtypes(self):
        pass

    def __init__(self, command, sfds, params=None, task_id=None):
        """
        Create SBusDatagram instance

        :param command: A string encoding the command to send
        :param sfds: A list of SBusFileDescriptor instances
        :param params: A optional dictionary with parameters for the command
                       execution
        :param task_id: An optional string task id. This is currently used for
                        cancel command
        """
        self.command = command
        fdtypes = [sfd.fdtype for sfd in sfds]
        self._check_required_fdtypes(fdtypes)
        self.sfds = sfds
        self.params = params
        self.task_id = task_id

    @property
    def num_fds(self):
        return len(self.sfds)

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
    def fds(self):
        """
        A list of raw file descriptors
        """
        return [sfd.fileno for sfd in self.sfds]

    @property
    def metadata(self):
        return [sfd.metadata for sfd in self.sfds]

    @property
    def serialized_metadata(self):
        return json.dumps(self.metadata)

    @property
    def object_in_metadata(self):
        return [sfd.storage_metadata for sfd in self.sfds
                if sfd.fdtype == sbus_fd.SBUS_FD_INPUT_OBJECT]

    @property
    def object_in_storlet_metadata(self):
        return [fd.storlets_metadata for fd in self.sfds
                if fd.fdtype == sbus_fd.SBUS_FD_INPUT_OBJECT]

    def _find_fds(self, fdtype):
        """
        Get a list of file descriptors for the given fd type

        :param fdtype: file descriptor type
        :returns: a list of file descriptors
        """
        return [sfd.fileno for sfd in self.sfds if sfd.fdtype == fdtype]

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

    def _check_required_fdtypes(self, given_fdtypes):
        if given_fdtypes[:len(self._required_fdtypes)] != \
                self._required_fdtypes:
            raise ValueError('Fd type mismatch given_fdtypes:%s \
                             required_fdtypes:%s' %
                             (given_fdtypes, self._required_fdtypes))

    def __str__(self):
        return 'num_fds=%s, md=%s, cmd_params=%s' % (
            self.num_fds,
            str(self.serialized_metadata),
            str(self.serialized_cmd_params))


class SBusServiceDatagram(SBusDatagram):
    """
    This class deals with datagram which only has one service out fd.

    This class is used to create datagram for some command type, which
    only needs one service out fd. Currently we can use this class for
    the following commands.
     - SBUS_CMD_HALT
     - SBUS_CMD_START_DAEMON
     - SBUS_CMD_STOP_DAEMON
     - SBUS_CMD_DAEMON_STATUS
     - SBUS_CMD_STOP_DAEMONS
     - SBUS_CMD_PING
     - SBUS_CMD_CANCEL
    """
    @property
    def _required_fdtypes(self):
        return [sbus_fd.SBUS_FD_SERVICE_OUT]

    def __init__(self, command, sfds, params=None, task_id=None):
        super(SBusServiceDatagram, self).__init__(
            command, sfds, params, task_id)

    @property
    def service_out_fd(self):
        return self._find_fd(sbus_fd.SBUS_FD_SERVICE_OUT)


class SBusExecuteDatagram(SBusDatagram):

    @property
    def _required_fdtypes(self):
        return [
            sbus_fd.SBUS_FD_SERVICE_OUT,
            sbus_fd.SBUS_FD_INPUT_OBJECT,
            sbus_fd.SBUS_FD_OUTPUT_OBJECT,
            sbus_fd.SBUS_FD_OUTPUT_OBJECT_METADATA,
            sbus_fd.SBUS_FD_LOGGER
        ]

    def __init__(self, command, sfds, params=None, task_id=None):
        # TODO(kota_): the args command is not used in ExecuteDatagram
        #              but it could be worthful to taransparent init
        #              for other datagram classes.
        # TODO(takashi): When we add extra output sources, we should
        #                consider how we can specify the number of the
        #                extra input/output sources, because currently
        #                this implementation is based on the idea that
        #                we only have extra input sources, which is
        #                added at the end of fd list
        extra_fdtypes = [sfd.fdtype for sfd in
                         sfds[len(self._required_fdtypes):]]

        if [t for t in extra_fdtypes if t != sbus_fd.SBUS_FD_INPUT_OBJECT]:
            raise ValueError(
                'Extra data should be SBUS_FD_INPUT_OBJECT')

        super(SBusExecuteDatagram, self).__init__(
            sbus_cmd.SBUS_CMD_EXECUTE, sfds, params, task_id)

    @property
    def invocation_fds(self):
        return [sfd.fileno for sfd in self.sfds[1:]]

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
    def logger_out_fd(self):
        return self._find_fd(sbus_fd.SBUS_FD_LOGGER)

    @property
    def object_in_fds(self):
        return self._find_fds(sbus_fd.SBUS_FD_INPUT_OBJECT)


def build_datagram(command, sfds, params, task_id):
    if command == sbus_cmd.SBUS_CMD_EXECUTE:
        dtg_cls = SBusExecuteDatagram
    else:
        dtg_cls = SBusServiceDatagram

    return dtg_cls(command, sfds, params, task_id)


def build_datagram_from_raw_message(fds, str_md, str_cmd_params):
    """
    Build SBusDatagram from raw message received over sbus

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

    if len(fds) != len(metadata):
        raise ValueError('Length mismatch fds: %d != md %d' %
                         (len(fds), len(metadata)))
    sfds = [SBusFileDescriptor.from_fileno_and_metadata_dict(fileno, md)
            for (fileno, md) in zip(fds, metadata)]
    return build_datagram(command, sfds, params, task_id)
