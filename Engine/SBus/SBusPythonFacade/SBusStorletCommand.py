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
21-Jul-2014    evgenyl    Initial implementation.
==========================================================================='''


'''------------------------------------------------------------------------'''
'''
@summary:   Enumerate Storlet Daemon commands.
@attention: The list should be synchronized
            with its Java counterpart.
'''

SBUS_CMD_HALT           = 0
SBUS_CMD_EXECUTE        = 1
SBUS_CMD_START_DAEMON   = 2
SBUS_CMD_STOP_DAEMON    = 3
SBUS_CMD_DAEMON_STATUS  = 4
SBUS_CMD_STOP_DAEMONS   = 5
SBUS_CMD_PING           = 6
SBUS_CMD_DESCRIPTOR     = 7
SBUS_CMD_CANCEL         = 8
SBUS_CMD_NOP            = 9

'''============================ END OF FILE ==============================='''
