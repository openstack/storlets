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
@author: gilv / cdoron / evgenyl
'''

from sys_test_params import *
from swiftclient import client as c

from storlets_test_utils import put_storlet_object, \
								                put_file_as_storlet_input_object
    
EXECDEP_PATH_TO_BUNDLE ='../StorletSamples/ExecDepStorlet/bin/'
EXECDEP_STORLET_NAME='execdepstorlet-1.0.jar'
EXECDEP_STORLET_LOG_NAME='execdepstorlet-1.0.log'
EXECDEP_JUNK_FILE = 'junk.txt'
EXECDEP_DEPS_NAMES=['get42']

'''------------------------------------------------------------------------'''
def put_storlet_executable_dependencies(url, token):
    resp = dict()
    for d in EXECDEP_DEPS_NAMES:                 
        metadata = {'X-Object-Meta-Storlet-Dependency-Version': '1',
                    'X-Object-Meta-Storlet-Dependency-Permissions': '0755' }
        
        f = open('%s/%s' %(EXECDEP_PATH_TO_BUNDLE, d),'r')  
        c.put_object(url, token, 'dependency', d, f, 
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
                        EXECDEP_STORLET_NAME, 
                        EXECDEP_PATH_TO_BUNDLE,
                        ','.join( str(x) for x in EXECDEP_DEPS_NAMES),
                        'com.ibm.storlet.execdep.ExecDepStorlet')
    put_storlet_executable_dependencies(url, token)
    put_file_as_storlet_input_object(url, 
									token, 
									EXECDEP_PATH_TO_BUNDLE,
									EXECDEP_JUNK_FILE )
    
'''------------------------------------------------------------------------'''
def invoke_storlet(url, token):
    metadata = {'X-Run-Storlet': EXECDEP_STORLET_NAME }
    resp = dict()
    resp_headers, gf = c.get_object(url, token, 
                                    'myobjects', 
                                    EXECDEP_JUNK_FILE, 
                                    response_dict=resp, 
                                    headers=metadata) 
    
    assert 'x-object-meta-depend-ret-code' in resp_headers
    assert resp_headers['x-object-meta-depend-ret-code'] == '42'
    assert resp['status'] == 200
          
    
'''------------------------------------------------------------------------'''
def main():
    os_options = {'tenant_name': ACCOUNT}
    url, token = c.get_auth( 'http://' + AUTH_IP + ":" 
                             + AUTH_PORT + '/v2.0', 
                             ACCOUNT + ':' + USER_NAME, 
                             PASSWORD, 
                             os_options = os_options, 
                             auth_version = '2.0' )
    
    print 'Deploying ExecDep storlet and dependencies'
    deploy_storlet(url, token)
    
    print "Invoking ExecDep storlet"
    invoke_storlet(url, token)
    
'''------------------------------------------------------------------------'''
if __name__ == "__main__":
    main()
