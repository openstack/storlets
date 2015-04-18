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

import json
import random
import string
from sys_test_params import *
from swiftclient import client as c

from storlets_test_utils import put_storlet_containers, put_storlet_object

'''------------------------------------------------------------------------'''
# Test Constants
PATH_TO_BUNDLE ='../StorletSamples/TestMetadataStorlet/bin/'
STORLET_NAME='testmetadatastorlet-1.0.jar'
STORLET_LOG_NAME='testmetadatastorlet-1.0.log'
SOURCE_FILE = 'source.txt'
'''------------------------------------------------------------------------'''
def put_storlet_input_object(url, token):
    resp = dict()
    metadata = {'X-Object-Meta-key1':'1',
                'X-Object-Meta-key2':'2',
                'X-Object-Meta-key3':'3',
                'X-Object-Meta-key4':'4',
                'X-Object-Meta-key5':'5',
                'X-Object-Meta-key6':'6',
                'X-Object-Meta-key7':'7',
                'X-Object-Meta-key8':'8',
                'X-Object-Meta-key9':'9',
                'X-Object-Meta-key10':'10'}
    f = open('%s/%s' %(PATH_TO_BUNDLE, SOURCE_FILE),'r')  
    c.put_object(url, token, 'myobjects', SOURCE_FILE, f, 
                 content_type = "application/octet-stream", 
                 headers = metadata, 
                 response_dict = resp)
    f.close()
    status = resp.get('status') 
    assert (status == 200 or status == 201)
 
'''------------------------------------------------------------------------'''
def deploy_storlet(url,token):
    #No need to create containers every time
    #put_storlet_containers(url, token)
    put_storlet_object( url, token,
                        STORLET_NAME,
                        PATH_TO_BUNDLE,
                        '',
                        'com.ibm.storlet.testmetadatastorlet.MetadataStorlet')
    put_storlet_input_object( url, token )
    
'''------------------------------------------------------------------------'''
def invoke_storlet(url, token,op, params = None, global_params = None):
    if params != None:
        querystring=''
        for key in params:
            querystring += '%s=%s,' % (key, params[key])
        querystring = querystring[:-1]
    else:
        querystring = None
            
    metadata = {'X-Run-Storlet': STORLET_NAME }
    if op == 'GET':
        # Get original object
        original_headers, original_content = c.get_object(url, token, 
                                        'myobjects', 
                                        SOURCE_FILE,
                                        response_dict=dict(),
                                        headers=metadata)
        assert(original_headers['X-Object-Meta-key1'.lower()] == '1')
        assert(original_headers['X-Object-Meta-key2'.lower()] == '2')
        assert(original_headers['X-Object-Meta-key3'.lower()] == '3')
        assert(original_headers['X-Object-Meta-key4'.lower()] == '4')
        assert(original_headers['X-Object-Meta-key5'.lower()] == '5')
        assert(original_headers['X-Object-Meta-key6'.lower()] == '6')
        assert(original_headers['X-Object-Meta-key7'.lower()] == '7')
        assert(original_headers['X-Object-Meta-key8'.lower()] == '8')
        assert(original_headers['X-Object-Meta-key9'.lower()] == '9')
        assert(original_headers['X-Object-Meta-key10'.lower()] == '10')
        assert(original_headers['X-Object-Meta-override_key'.lower()] == 'new_value')
        
'''------------------------------------------------------------------------'''
def main():
    os_options = {'tenant_name': ACCOUNT}
    url, token = c.get_auth( 'http://' + AUTH_IP + ":" 
                             + AUTH_PORT + '/v2.0', 
                             ACCOUNT + ':' + USER_NAME, 
                             PASSWORD, 
                             os_options = os_options, 
                             auth_version = '2.0' )
    
    print 'Deploying storlet and dependencies'
    deploy_storlet(url, token)
    
    print "Invoking storlet on GET"
    invoke_storlet(url, token,'GET')
    
'''------------------------------------------------------------------------'''
if __name__ == "__main__":
    main()
