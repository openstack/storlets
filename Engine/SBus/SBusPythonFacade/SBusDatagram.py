'''-------------------------------------------------------------------------
Copyright IBM Corp. 2015, 2015 All Rights Reserved
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
Limitations under the License.
-------------------------------------------------------------------------'''

'''===========================================================================
15-Jul-2014    evgenyl    Initial implementation.
21-Jul-2014    evgenyl    Extending API: create_service_datagram,
                                         get_first_file_of_type
28-Jul-2014    evgenyl    Bugfix in create_service_datagram - meta shall be
                          dictionary of dictionaries
==========================================================================='''

import json
import os
import syslog

from SBusFileDescription import SBUS_FD_OUTPUT_OBJECT
from SBusStorletCommand import SBUS_CMD_NOP

'''------------------------------------------------------------------------'''


class SBusDatagram(object):
    '''@summary: This class aggregates data to be transferred

              using SBus functionality.
    '''

    command_dict_key_name_ = 'command'
    task_id_dict_key_name_ = 'taskId'

    '''--------------------------------------------------------------------'''

    def __init__(self):
        '''@summary:              CTOR

        @ivar e_command_ :     A command to Storlet Daemon.
        @type e_command_ :     Integer. SBusStorletCommand enumerated value.
        @ivar h_files_:        List of open file descriptors.
        @type h_files_:        List of integers.
        @ivar n_files_:        Quantity of file descriptors.
        @type n_files_:        Integer.
        @ivar files_metadata_: Meta-data for the file descriptors.
        @type files_metadata_: List of Dictionaries String-to-String.
        @ivar exec_params_:    Auxiliary parameters for e_command_.
        @type exec_params_:    Dictionary String-to-String.

        @invariant:            Quantity of entries in files_metadata_ list
                               is the same as in h_files_, i.e. n_files_.
        '''
        self.e_command_ = SBUS_CMD_NOP
        self.task_id_ = None
        self.h_files_ = None
        self.n_files_ = 0
        self.files_metadata_ = None
        self.exec_params_ = None

    '''--------------------------------------------------------------------'''

    @staticmethod
    def create_service_datagram(command,
                                outfd):
        '''@summary:       Datagram static factory.

                        Create "service" datagram, i.e.
                        - command shall be one of
                          {PING, START/STOP/STATUS-DAEMON}
                        - single output file descriptor

        @param command: Command to send
        @type  command: SBusStorletCommand
        @param outfd:   Output stream for command execution results
        @type  outfd:   File descriptor or Integer

        @return:        A datagram with the required data
        @rtype:         SBusDatagram
        '''
        dtg = SBusDatagram()
        dtg.set_command(command)
        meta = {}
        meta[0] = {'type': SBUS_FD_OUTPUT_OBJECT}
        files = []
        if isinstance(outfd, file):
            files.append(outfd.fileno())
        else:
            files.append(outfd)
        dtg.set_files(files)
        dtg.set_metadata(meta)
        return dtg

    '''--------------------------------------------------------------------'''

    def from_raw_data(self,
                      h_files,
                      str_json_metadata,
                      str_json_params):
        '''@summary:                 CTOR

                                  Construct object from file list and
                                  two JSON-encoded strings.

        @param h_files:           List of file descriptors.
        @type  h_files:           List of integers.
        @param str_json_metadata: JSON encoding of file descriptors meta-data.
        @type  str_json_metadata: String.
        @param str_json_params:   JSON encoding for execution parameters.
        @type  str_json_params:   String.

        @rtype:                   void
        '''
        self.set_files(h_files)
        self.extract_metadata(str_json_metadata)
        self.extract_params(str_json_params)

    '''--------------------------------------------------------------------'''

    def extract_metadata(self,
                         str_json_metadata):
        '''@summary:                 Extract files_metadata array

                                  of dictionaries form a JSON string
        @requires:                n_files_ has to be se

        @param str_json_metadata: JSON encoding of file descriptors meta-data.
        @type  str_json_metadata: String.

        @rtype:                   void
        '''
        if self.get_num_files() > 0:
            all_metadata = json.loads(str_json_metadata)
            self.files_metadata_ = []
            for i in range(self.get_num_files()):
                str_curr_metadata = all_metadata[str(i)]
                self.files_metadata_.append(json.loads(str_curr_metadata))

    '''--------------------------------------------------------------------'''

    def extract_params(self, str_json_params):
        '''@summary:               Extract command field and exec_params

                                dictionary form a JSON string
        @param str_json_params: JSON encoding for the execution parameters.
        @type  str_json_params: string.

        @rtype:                 void
        '''
        ext_params = json.loads(str_json_params)
        cmd = self.command_dict_key_name_
        tid = self.task_id_dict_key_name_
        if cmd in ext_params:
            self.e_command_ = ext_params[cmd]
            ext_params.pop(cmd, None)
        elif tid in ext_params:
            self.task_id_ = ext_params[tid]
            ext_params.pop(tid, None)
        else:
            self.e_command_ = SBUS_CMD_NOP
        b_exec_params_is_not_empty = len(ext_params.keys()) > 0
        if b_exec_params_is_not_empty:
            self.exec_params_ = ext_params.copy()
        else:
            self.exec_params_ = None

    '''--------------------------------------------------------------------'''

    def get_params_and_cmd_as_json(self):
        '''@summary: Convert command field and execution parameters

                  dictionary into JSON as the following -
                  1. Copy exec_params_. Initialize the combined dictionary.
                  2. Push the next pair into the combined dictionary
                     key   - 'command'
                     value - e_command_

        @return:  JSON encoded representation of exec_params_ and command_
        @rtype:   string
        '''
        exec_params = {}
        if self.exec_params_:
            exec_params = self.exec_params_.copy()
        cmd = self.command_dict_key_name_
        exec_params[cmd] = self.e_command_
        if self.task_id_:
            tid = self.task_id_dict_key_name_
            exec_params[tid] = self.task_id_
        str_result = json.dumps(exec_params)
        return str_result

    '''--------------------------------------------------------------------'''

    def get_files_metadata_as_json(self):
        '''@summary: Encode the list of dictionaries into JSON as the following

                  1. Create a combined dictionary (Integer-to-String)
                     Key   - index in the original list
                     Value - JSON encoding of the certain dictionary
                  2. Encode the combined dictionary into JSON

        @return:  List of dictionaries into a JSON string.
        @rtype:   string
        '''
        all_metadata = {}
        str_result = None
        for i in range(self.get_num_files()):
            all_metadata[str(i)] = json.dumps(self.files_metadata_[i])
        if self.get_num_files() > 0:
            str_result = json.dumps(all_metadata)
        return str_result

    '''--------------------------------------------------------------------'''

    def get_num_files(self):
        '''@summary: Getter.

        @return:  The quantity of file descriptors.
        @rtype:   integer
        '''
        return self.n_files_

    '''--------------------------------------------------------------------'''

    def get_files(self):
        '''@summary: Getter.

        @return:  The list of file descriptors.
        @rtype:   List of integers
        '''
        return self.h_files_

    '''--------------------------------------------------------------------'''

    def set_files(self, h_files):
        '''@summary:       Setter.

                        Assign file handlers list and update n_files_ field

        @param h_files: File descriptors.
        @type  h_files: List of integers

        @rtype:         void
        '''
        if not h_files:
            self.n_files_ = 0
        else:
            self.n_files_ = len(h_files)
        self.h_files_ = None
        if 0 < self.n_files_:
            self.h_files_ = []
            for i in range(self.n_files_):
                if isinstance(h_files[i], file):
                    self.h_files_.append(h_files[i].fileno())
                else:
                    self.h_files_.append(h_files[i])

    '''--------------------------------------------------------------------'''

    def get_first_file_of_type(self, file_type):
        '''@summary:         Iterate through file list and metadata.

                          Find the first file with the required type

        @param file_type: The file type to look for
        @type  file_type: Integer, SBusFileDescription enumerator

        @return:          File descriptor or None if not found
        @rtype:           File
        '''
        required_file = None
        for i in range(self.get_num_files()):
            if (self.get_metadata()[i])['type'] == file_type:
                try:
                    required_file = os.fdopen(self.get_files()[i], 'w')
                except IOError as err:
                    syslog.syslog(syslog.LOG_DEBUG,
                                  'Failed to open file: %s' % err.strerror)
        return required_file

    '''--------------------------------------------------------------------'''

    def get_metadata(self):
        '''@summary: Getter.

        @return:  The list of meta-data dictionaries.
        @rtype:   List of dictionaries
        '''
        return self.files_metadata_

    '''--------------------------------------------------------------------'''

    def set_metadata(self, metadata):
        '''@summary:        Setter.

                         Assign file_metadata_ field

        @param metadata: File descriptors meta-data dictionaries.
        @type  metadata: List of dictionaries

        @rtype:          void
        '''
        self.files_metadata_ = metadata

    '''--------------------------------------------------------------------'''

    def get_exec_params(self):
        '''@summary: Getter.

        @return:  The execution parameters dictionary.
        @rtype:   Dictionary
        '''
        return self.exec_params_

    '''--------------------------------------------------------------------'''

    def set_exec_params(self, params):
        '''@summary:      Setter.

                       Assign execution parameters dictionary.

        @param params: Execution parameters to assign
        @type  params: Dictionary

        @rtype:        void

        '''
        self.exec_params_ = params

    '''--------------------------------------------------------------------'''

    def add_exec_param(self, param_name, param_value):
        '''@summary:        Add a single pair to the exec_params_ dictionary

                            Don't change if the parameter exists already

        @param param_name:  Execution parameter name to be added
        @type  param_name:  string
        @param param_value: Execution parameter value
        @type  param_value: Unknown

        @return:            False if param_name exists already
        @rtype:             boolean
        '''
        b_status = True
        if not self.get_exec_params():
            exec_params = {}
            exec_params[param_name] = param_value
            self.set_exec_params(exec_params)
        elif param_name in self.get_exec_params():
            b_status = False
        else:
            self.get_exec_params()[param_name] = param_value
        return b_status

    '''--------------------------------------------------------------------'''

    def get_command(self):
        '''@summary: Getter.

        @return:  The Storlet Daemon command.
        @rtype:   SBusStorletCommand
        '''
        return self.e_command_

    '''--------------------------------------------------------------------'''

    def set_command(self, cmd):
        '''@summary:   Setter.

                    Assign Storlet Daemon command.

        @param cmd: Command to assign
        @type  cmd: SBusStorletCommand enumerator

        @rtype:     void
        '''
        self.e_command_ = cmd

    '''--------------------------------------------------------------------'''

    def get_task_id(self):
        '''@summary: Getter.

        @return:  The task id.
        @rtype:   string
        '''
        return self.task_id_

    '''--------------------------------------------------------------------'''

    def set_task_id(self, taskId):
        '''@summary:   Setter.

                    Assign task id

        @param taskId: Command to assign
        @type  taskId: string

        @rtype:     void
        '''
        self.task_id_ = taskId

    '''--------------------------------------------------------------------'''

    @staticmethod
    def dictionaies_equal(d1, d2):
        '''@summary: Check whether two dictionaries has the same content.

                  The order of the entries is not considered.

        @return:  The answer to the above
        @rtype:   boolean.
        '''
        diffr = set(d1.items()) ^ set(d2.items())
        return (0 == len(diffr))

'''============================ END OF FILE ==============================='''
