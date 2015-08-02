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
24-Jul-2014    evgenyl    Start/Stop-logger are static methods.
==========================================================================='''

import ctypes
from SBusDatagram import SBusDatagram

from ctypes import c_char_p
from ctypes import c_int
from ctypes import POINTER

'''------------------------------------------------------------------------'''


class SBus(object):
    '''
    @summary: This class wraps low level C-API for SBus functionality
              to be used with Python
    '''
    SBUS_SO_NAME = '/usr/local/lib/python2.7/dist-packages/sbus.so'

    '''--------------------------------------------------------------------'''
    def __init__(self):
        '''
        @summary:             CTOR
                              Setup argument types mappings.
        '''

        # load the C-library
        self.sbus_back_ = ctypes.CDLL(SBus.SBUS_SO_NAME)

        # create SBus
        self.sbus_back_.sbus_create.argtypes   = [c_char_p]
        self.sbus_back_.sbus_create.restype    =  c_int

        # listen to SBus
        self.sbus_back_.sbus_listen.argtypes   = [c_int]
        self.sbus_back_.sbus_listen.restype    =  c_int

        # send message
        self.sbus_back_.sbus_send_msg.argtypes = [c_char_p,
                                                  POINTER(c_int),
                                                  c_int,
                                                  c_char_p,
                                                  c_int,
                                                  c_char_p,
                                                  c_int]
        self.sbus_back_.sbus_send_msg.restype  =  c_int

        # receive message
        self.sbus_back_.sbus_recv_msg.argtypes = [c_int,
                                                  POINTER(POINTER(c_int)),
                                                  POINTER(c_int),
                                                  POINTER(c_char_p),
                                                  POINTER(c_int),
                                                  POINTER(c_char_p),
                                                  POINTER(c_int)]
        self.sbus_back_.sbus_recv_msg.restype  =  c_int

    '''--------------------------------------------------------------------'''
    @staticmethod
    def start_logger(str_log_level='DEBUG', container_id=None):
        '''
        @summary:             Start logger.

        @param str_log_level: The level of verbosity in log records.
                              Default value - 'DEBUG'.
        @type  str_log_level: string

        @rtype:               void
        '''
        # load the C-library
        sbus_back_ = ctypes.CDLL(SBus.SBUS_SO_NAME)

        sbus_back_.sbus_start_logger.argtypes = [c_char_p, c_char_p]
        sbus_back_.sbus_start_logger(str_log_level, container_id)

    '''--------------------------------------------------------------------'''
    @staticmethod
    def stop_logger():
        '''
        @summary: Stop logger.

        @rtype:   void
        '''
        # load the C-library
        sbus_back_ = ctypes.CDLL(SBus.SBUS_SO_NAME)
        sbus_back_.sbus_stop_logger()

    '''--------------------------------------------------------------------'''
    def create(self, sbus_name):
        '''
        @summary:         Instantiate an SBus. A wrapper for C function.

        @param sbus_name: Path to domain socket "file".
        @type  sbus_name: string

        @return:          Handler to the opened SBus.
        @rtype:           integer
        '''
        return self.sbus_back_.sbus_create(sbus_name)

    '''--------------------------------------------------------------------'''
    def listen(self, sbus_handler):
        '''
        @summary:            Listen to the SBus.
                             Suspend the executing thread.

        @param sbus_handler: Handler to SBus to listen.
        @type  sbus_handler: integer

        @return:             Status, whether SBus is listened successfully.
        @rtype:              integer
        '''
        return self.sbus_back_.sbus_listen(sbus_handler)

    '''--------------------------------------------------------------------'''
    def receive(self, sbus_handler):
        '''
        @summary:            Read the data from SBus.
                             Create a datagram.

        @param sbus_handler: Handler to SBus to read data from.
        @type  sbus_handler: integer

        @return:             An object with the obtained data. Null-able.
        @rtype:              SBusDatagram
        '''
        ph_files    = POINTER(c_int)()
        pp_metadata = (c_char_p)()
        pp_params   = (c_char_p)()
        pn_files    = (c_int)()
        pn_metadata = (c_int)()
        pn_params   = (c_int)()

        # Invoke C function
        n_status = self.sbus_back_.sbus_recv_msg(sbus_handler,
                                                 ph_files,
                                                 pn_files,
                                                 pp_metadata,
                                                 pn_metadata,
                                                 pp_params,
                                                 pn_params)
        result_dtg   = None
        if 0 <= n_status:
            # The invocation was successful.
            # De-serialize the data

            # Aggregate file descriptors
            n_files = pn_files.value
            h_files = []
            for i in range(n_files):
                h_files.append(ph_files[i])

            # Extract Python strings
            n_metadata   = pn_metadata.value
            str_metadata = pp_metadata.value
            n_params     = pn_params.value
            str_params   = pp_params.value

            # Trim the junk out
            if 0 < n_metadata:
                str_metadata = str_metadata[0:n_metadata]
            str_params = str_params[0:n_params]

            # Construct actual result datagram
            result_dtg = SBusDatagram()
            result_dtg.from_raw_data(h_files,
                                     str_metadata,
                                     str_params)
        return result_dtg

    '''--------------------------------------------------------------------'''
    @staticmethod
    def send(sbus_name, datagram):
        '''
        @summary:         Send the datagram through SBus.
                          Serialize dictionaries into JSON strings.

        @param sbus_name: Path to domain socket "file".
        @type  sbus_name: string
        @param datagram:  The object to send
        @type  datagram:  SBusDatagram

        @return:          Status of the operation
        @rtype:           integer
        '''

        # Serialize the datagram into JSON strings and C integer array
        str_json_params = datagram.get_params_and_cmd_as_json()
        p_params        = c_char_p(str_json_params)
        n_params        = c_int(len(str_json_params))

        n_files         = c_int(0)
        h_files         = None
        n_metadata      = c_int(0)
        p_metadata      = None

        if datagram.get_num_files() > 0:
            str_json_metadata = datagram.get_files_metadata_as_json()
            p_metadata        = c_char_p(str_json_metadata)
            n_metadata        = c_int(len(str_json_metadata))

            n_fds             = datagram.get_num_files()
            n_files           = c_int(n_fds)

            file_fds          = datagram.get_files()
            h_files           = (c_int * n_fds)()

            for i in range(n_fds):
                h_files[i] = file_fds[i]

        # Invoke C function
        sbus     = SBus()
        n_status = sbus.sbus_back_.sbus_send_msg(sbus_name,
                                                 h_files,
                                                 n_files,
                                                 p_metadata,
                                                 n_metadata,
                                                 p_params,
                                                 n_params)
        return n_status


'''============================ END OF FILE ==============================='''
