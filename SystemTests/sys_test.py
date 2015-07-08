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
@author: gilv
'''

import threading
import time
import json
import os
import random
import string
import tarfile

from sys_test_params import *
from swiftclient import client as c
from swiftclient.client import encode_utf8, http_connection

from storlets_test_utils import enable_account_for_storlets, \
     put_dependency, put_storlet_containers, put_storlet_object

TEST_STORLET_NAME='test-10.jar'
 
PATH_TO_STORLET_GIT_MODULE = ''
PATH_TO_STORLETS = ''

'''------------------------------------------------------------------------'''
def invokeTestStorlet(url, token, op, withlog=False):
    headers = {'X-Run-Storlet':TEST_STORLET_NAME}
    if withlog == True:
        headers['X-Storlet-Generate-Log'] = 'True'

    params = 'op={0}&param2=val2'.format(op)
    resp_dict = dict()
    try:
        resp_headers, gf = c.get_object(url, token, 'myobjects', 
                                        'test_object', None, None, params, 
                                        resp_dict, headers)
        #print resp_dict
        get_text = gf
        #print get_text
        get_response_status = resp_dict.get('status')
        
        if withlog == True:
            resp_headers, gf = c.get_object(url, token, 
                                            'storletlog', 'test.log', 
                                            None, None, None, None, headers)
            assert resp_headers.get('status') == 200
            text = gf.read()
            assert resp_headers.get('status') == 200
            #print text
        
        if op == 'print':
            assert get_response_status == 200
            assert 'op' in get_text
            assert 'print' in get_text
            assert 'param2' in get_text
            assert 'val2' in get_text

    except Exception as e:
        get_response_status = resp_dict.get('status')
        if op == 'crash':
            print get_response_status
            assert get_response_status >= 500 or get_response_status == 404
    
        if op == 'hold':
            #print get_response_status
            assert get_response_status >= 500 or get_response_status == 404

        if op == 'print':
            #print get_response_status
            raise e
        
'''------------------------------------------------------------------------'''
class myTestThread (threading.Thread):
    def __init__(self, url, token):
        threading.Thread.__init__(self)
        self.token = token
        self.url = url
    def run(self):
        invokeTestStorlet(self.url, self.token, "print", False)

'''------------------------------------------------------------------------'''
def invokeTestStorletinParallel(url, token):
    mythreads = []

    for i in range(10):
        new_thread = myTestThread(url, token)
        mythreads.append(new_thread)

    for t in mythreads:
        t.start()
        
    for t in mythreads:
        t.join()

'''------------------------------------------------------------------------'''
def testTestStorlet(url, token):
    print "Deploying test storlet"
    put_storlet_object(url, 
                       token, 
                       TEST_STORLET_NAME,
                       "%s/TestStorlet/bin/" % PATH_TO_STORLETS,
                       '', 
                       'com.ibm.storlet.test.test1')

    print "uploading object to execute test upon"
    c.put_object(url,
                 token,
                 'myobjects',
                 'test_object',
                 'some content')
    print "Invoking test storlet to print"
    invokeTestStorlet(url, token, "print", False)
    print "Invoking test storlet to crash"
    invokeTestStorlet(url, token, "crash")
    print "Invoking test storlet to hold"
    invokeTestStorlet(url, token, "hold")
    print "Invoking test storlet to print"
    invokeTestStorlet(url, token, "print", False)
    print "Invoking test storlet in parallel to print"
    invokeTestStorletinParallel(url, token)


'''------------------------------------------------------------------------'''
def init_path_dependant_params():
    global PATH_TO_STORLET_GIT_MODULE 
    global PATH_TO_STORLETS
    PATH_TO_STORLET_GIT_MODULE = '../'
    if PATH_TO_STORLET_GIT_MODULE == '':
        PATH_TO_STORLET_GIT_MODULE = os.environ['HOME'] + \
                                     '/workspace/Storlets'
    PATH_TO_STORLETS='%s/StorletSamples' % PATH_TO_STORLET_GIT_MODULE
    
'''------------------------------------------------------------------------'''
def main():
    init_path_dependant_params()

    print 'Getting token'
    os_options = {'tenant_name': ACCOUNT}
    url, token = c.get_auth("http://" + AUTH_IP + ":" + AUTH_PORT \
                            + "/v2.0", ACCOUNT + ":" + USER_NAME, 
                            PASSWORD, os_options = os_options, 
                            auth_version="2.0")

    print 'Creating myobjects container'
    c.put_container(url, token, 'myobjects')
    
    print 'Invoking test storlet'    
    testTestStorlet(url, token)

    os.system('python execdep_test.py')
    os.system('python identity_storlet_test.py')
    os.system('python half_storlet_test.py')
    os.system('python metadata_storlet_test.py')
    os.system('python SLO_test.py')
    
'''------------------------------------------------------------------------'''
if __name__ == "__main__":
    main()
