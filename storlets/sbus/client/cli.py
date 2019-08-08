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
import os
from sys import exit
from storlets.sbus.client import SBusClient
from storlets.sbus.client.exceptions import SBusClientException

EXIT_SUCCESS = 0
EXIT_ERROR = 1


def main(argv):
    # TODO(takashi): Add more detailed help message

    if len(argv) < 3:
        print('sbus <command> <pipe_path>')
        exit(EXIT_ERROR)

    command = argv[1]
    pipe_path = argv[2]

    if not os.path.exists(pipe_path):
        print('ERROR: Pipe file %s does not exist' % pipe_path)
        exit(EXIT_ERROR)

    client = SBusClient(pipe_path)
    try:
        handler = getattr(client, command)

        # TODO(takashi): Currently this only works for ping or halt.
        #                We need to pass more parameters like storlet_name
        #                to implement the other command types.
        resp = handler()
    except (AttributeError, NotImplementedError):
        print('ERROR: Command %s is not supported' % command)
        exit(EXIT_ERROR)
    except SBusClientException as err:
        print('ERROR: Failed to send sbus command %s to %s: %s'
              % (command, pipe_path, err))
        exit(EXIT_ERROR)
    except Exception as err:
        print('ERROR: Unknown error: %s' % err)
        exit(EXIT_ERROR)

    print('Response: %s: %s' % (resp.status, resp.message))
    if resp.status:
        print('OK')
        exit(EXIT_SUCCESS)
    else:
        print('ERROR: Got error response')
        exit(EXIT_ERROR)
