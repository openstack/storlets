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

import os
import sys

from storlets.sbus import SBus
from storlets.sbus.datagram import FDMetadata, SBusServiceDatagram
from storlets.sbus.file_description import SBUS_FD_SERVICE_OUT
from storlets.sbus.command import SBUS_CMD_HALT


def print_usage(argv):
    print(argv[0] + ' /path/to/daemon/factory_pipe')
    print('Example:')
    sys.stdout.write(argv[0] + ' ')
    print('/home/docker_device/pipes/scopes/'
          'AUTH_fb8b63c579054c48816ca8acd090b3d9/factory_pipe')


def main(argv):
    if len(argv) < 2:
        print_usage(argv)
        return

    daemon_factory_pipe_name = argv[1]
    try:
        fi, fo = os.pipe()
        halt_dtg = SBusServiceDatagram(
            SBUS_CMD_HALT,
            [fo],
            [FDMetadata(SBUS_FD_SERVICE_OUT).to_dict()])
        n_status = SBus.send(daemon_factory_pipe_name, halt_dtg)
        if n_status < 0:
            print('Sending failed')
        else:
            print('Sending succeeded')
            cmd_response = os.read(fi, 256)
            print(cmd_response)
    finally:
        os.close(fi)
        os.close(fo)


if __name__ == '__main__':
    main(sys.argv)
