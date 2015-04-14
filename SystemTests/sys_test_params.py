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
'''
IMPORTANT: Make sure the variables AUTH_PI and KEYSTONE_IP point to the system 
you are testing!!!
'''
'''------------------------------------------------------------------------'''
# Establishing Swift connection, user ID, etc
PROXY_PROTOCOL = 'HTTP'
AUTH_PROTOCOL = 'HTTP'
DEV_AUTH_IP = '127.0.0.1'
AUTH_IP = DEV_AUTH_IP
PROXY_PORT = '80'
AUTH_PORT = '5000'

ACCOUNT = 'service'
USER_NAME = 'swift'
PASSWORD = 'passw0rd'
