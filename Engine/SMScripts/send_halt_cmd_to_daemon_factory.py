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
02-Dec-2014    evgenyl    Initial implementation.
==========================================================================='''

import os
import sys

from SBusPythonFacade.SBus import SBus
from SBusPythonFacade.SBusDatagram import SBusDatagram
from SBusPythonFacade.SBusStorletCommand import SBUS_CMD_HALT

'''------------------------------------------------------------------------'''


def print_usage(argv):
    print(argv[0] + ' /path/to/daemon/factory_pipe')
    print('Example:')
    sys.stdout.write(argv[0] + ' ')
    print('/home/lxc_device/pipes/scopes/'
          'AUTH_fb8b63c579054c48816ca8acd090b3d9/factory_pipe')

'''------------------------------------------------------------------------'''


def main(argv):
    if 2 > len(argv):
        print_usage(argv)
        return

    daemon_factory_pipe_name = argv[1]
    fi, fo = os.pipe()
    halt_dtg = SBusDatagram.create_service_datagram(SBUS_CMD_HALT, fo)
    n_status = SBus.send(daemon_factory_pipe_name, halt_dtg)
    if 0 > n_status:
        print('Sending failed')
    else:
        print('Sending succeeded')
        cmd_response = os.read(fi, 256)
        print(cmd_response)
    os.close(fi)
    os.close(fo)

'''------------------------------------------------------------------------'''
if __name__ == '__main__':
    main(sys.argv)

'''============================ END OF FILE ==============================='''
