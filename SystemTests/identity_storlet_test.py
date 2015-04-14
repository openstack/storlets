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

import os
import json
import random
import string
from sys_test_params import *
from swiftclient import client as c

from storlets_test_utils import put_storlet_containers, put_storlet_object, \
     progress, progress_ln, progress_msg

'''------------------------------------------------------------------------'''
# Test Constants
IDENTITY_PATH_TO_BUNDLE ='../StorletSamples/IdentityStorlet/bin/'
IDENTITY_STORLET_NAME='identitystorlet-1.0.jar'
IDENTITY_STORLET_LOG_NAME='identitystorlet-1.0.log'
IDENTITY_SOURCE_FILE = 'source.txt'
IDENTITY_DEPS_NAMES=['get42']

    
'''------------------------------------------------------------------------'''
def put_storlet_executable_dependencies(url, token):
    resp = dict()
    for d in IDENTITY_DEPS_NAMES:                 
        metadata = {'X-Object-Meta-Storlet-Dependency-Version': '1',
                    'X-Object-Meta-Storlet-Dependency-Permissions': '0755' }
        
        f = open('%s/%s' %(IDENTITY_PATH_TO_BUNDLE, d),'r')  
        c.put_object(url, token, 'dependency', d, f, 
                     content_type = "application/octet-stream", 
                     headers = metadata,
                     response_dict = resp)
        f.close()
        status = resp.get('status') 
        assert (status == 200 or status == 201)

'''------------------------------------------------------------------------'''
def put_storlet_input_object(url, token):
    resp = dict()
    metadata = {'X-Object-Meta-Testkey':'tester'}
    f = open('%s/%s' %(IDENTITY_PATH_TO_BUNDLE, IDENTITY_SOURCE_FILE),'r')  
    c.put_object(url, token, 'myobjects', IDENTITY_SOURCE_FILE, f, 
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
                        IDENTITY_STORLET_NAME,
                        IDENTITY_PATH_TO_BUNDLE,
                        ','.join( str(x) for x in IDENTITY_DEPS_NAMES),
                        'com.ibm.storlet.identity.IdentityStorlet')
    put_storlet_executable_dependencies(url, token)
    put_storlet_input_object( url, token )
    
'''------------------------------------------------------------------------'''
def invoke_storlet_on_1GB_file(url, token):
    GBFile = open('/tmp/1GB_file','w')
    for _ in range(128):
        progress()
        uploaded_content = ''.join('1' for _ in range(8*1024*1024))
        GBFile.write(uploaded_content)
    GBFile.close()
    
    headers = {'X-Run-Storlet': IDENTITY_STORLET_NAME }
    GBFile = open('/tmp/1GB_file','r')
    response=dict()
    progress()
    c.put_object(url, token, 'myobjects', '1GBFile', GBFile, 
                 1024*1024*1024, None, None, "application/octet-stream", 
                 headers, None, None, None, response)
    progress()
    status = response.get('status') 
    assert (status == 200 or status == 201)
    progress()
    os.remove('/tmp/1GB_file')
    progress_ln()
    
    
def invoke_storlet(url, token, op, params = None, global_params = None):
    if params != None:
        querystring=''
        for key in params:
            querystring += '%s=%s,' % (key, params[key])
        querystring = querystring[:-1]
    else:
        querystring = None
            
    metadata = {'X-Run-Storlet': IDENTITY_STORLET_NAME}
    if op == 'GET':
        # Get original object
        original_headers, original_content = c.get_object(url, token, 
                                        'myobjects', 
                                        IDENTITY_SOURCE_FILE,
                                        response_dict=dict())
        #print original_headers
        file_length = int(original_headers['content-length'])
        processed_headers, returned_content = c.get_object(url, token, 
                                        'myobjects', 
                                        IDENTITY_SOURCE_FILE,
                                        query_string = querystring, 
                                        response_dict=dict(), 
                                        headers=metadata,
                                        resp_chunk_size = file_length)
        processed_content = ''
        for chunk in returned_content:
            if chunk:
                processed_content+=chunk
                            
        if params != None and params.get('execute',None) != None:
            assert(processed_headers['X-Object-Meta-Execution result'.lower()] == '42')
        if params != None and params.get('double',None) == 'true':
            assert(original_content==processed_content[:file_length])
            assert(original_content==processed_content[file_length:])
        else:
            assert(original_content == processed_content)
        assert(original_headers['X-Object-Meta-Testkey'.lower()] == processed_headers['X-Object-Meta-Testkey'.lower()])
        
    if op == 'PUT':
        # PUT a random file
        response = dict()
        uploaded_content = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(1024))
        random_md = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(32))
        #content_length = 1024
        content_length = None
        headers = {'X-Run-Storlet': IDENTITY_STORLET_NAME, 
                   'X-Object-Meta-Testkey' : random_md }
        c.put_object(url, token, 'myobjects', 'identity_random_source', uploaded_content, 
                 content_length, None, None, "application/octet-stream", 
                 headers, None, None, querystring, response)
        resp_headers, saved_content = c.get_object(url, token, 
                'myobjects', 
                'identity_random_source', 
                response_dict=dict())
        
        if params != None and params.get('double',None) == 'true':
            assert(uploaded_content==saved_content[:1024])
            assert(uploaded_content==saved_content[1024:])
        else:
            assert(uploaded_content == saved_content)            
        
        if params != None and params.get('execute',None) != None:
            assert(resp_headers['X-Object-Meta-Execution result'.lower()] == '42')
             
        assert(resp_headers['X-Object-Meta-Testkey'.lower()] == random_md)                

'''------------------------------------------------------------------------'''
def main():
    os_options = {'tenant_name': ACCOUNT}
    url, token = c.get_auth( 'http://' + AUTH_IP + ":" 
                             + AUTH_PORT + '/v2.0', 
                             ACCOUNT + ':' + USER_NAME, 
                             PASSWORD, 
                             os_options = os_options, 
                             auth_version = '2.0' )
    
    print 'Deploying Identity storlet and dependencies'
    
    deploy_storlet(url, token)
    
    print "Invoking Identity storlet on PUT"
    invoke_storlet(url, token,'PUT')
    progress_msg("Invoking Identity storlet on 1GB file PUT")
    invoke_storlet_on_1GB_file(url, token)    
    print "Invoking Identity storlet on PUT with execution of dependency"
    invoke_storlet(url, token,'PUT', {'execute' : 'true'})
    print "Invoking Identity storlet on PUT with double"
    invoke_storlet(url, token,'PUT', {'double' : 'true'})
    print "Invoking Identity storlet on GET"
    invoke_storlet(url, token,'GET')
    print "Invoking Identity storlet on GET with double"
    invoke_storlet(url, token,'GET', {'double' : 'true'})
    print "Invoking Identity storlet on GET with execution of dependency"
    invoke_storlet(url, token,'GET',{'execute' : 'true'})
    print "Invoking Identity storlet in Task"
    
'''------------------------------------------------------------------------'''
if __name__ == "__main__":
    main()