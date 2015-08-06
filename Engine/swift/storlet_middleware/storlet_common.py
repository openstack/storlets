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
Created on Feb 18, 2014

@author: gilv
'''
import os
import sys
import traceback


class StorletTimeout(Exception):
    pass


class StorletLogger(object):
    def __init__(self, path, name):
        self.full_path = os.path.join(path, '%s.log' % name)

    def open(self):
        self.file = open(self.full_path, 'a')

    def getfd(self):
        return self.file.fileno()

    def getsize(self):
        statinfo = os.stat(self.full_path)
        return statinfo.st_size

    def close(self):
        self.file.close()

    def fobj(self):
        return open(self.full_path, 'r')


class StorletException(object):

    # Print details about the code line which caused the exception
    @staticmethod
    def handle(logger, exc):
        logger.info('-' * 60)
        logger.info(exc)
        # logging.exception()
        traceback.print_exc(file=sys.stdout)
        logger.info('-' * 60)


class StorletGatewayBase(object):

    def validateStorletUpload(self, request):
        raise NotImplementedError("Not implemented: validateStorletUpload")

    def authorizeStorletExecution(self, request):
        raise NotImplementedError("Not implemented: authorizeStorletExecution")

    def augmentStorletRequest(self, request):
        raise NotImplementedError("Not implemented: augmentStorletRequest")

    def gatewayProxyPutFlow(self, orig_request, container, obj):
        raise NotImplementedError("Not implemented: gatewayProxyPutFlow")

    def gatewayProxySloFlow(self, request, container, obj, original_response):
        raise NotImplementedError("Not implemented: gatewayProxySloFlow")

    def gatewayObjectGetFlow(self, request, container, obj, original_response):
        raise NotImplementedError("Not implemented: gatewayObjectGetFlow")


class StorletStubGateway(StorletGatewayBase):

    def __init__(self, sconf, logger, app, version, account, container,
                 obj):
        self.logger = logger
        self.app = app
        self.version = version
        self.account = account
        self.container = container
        self.obj = obj
        self.sconf = sconf
        self.dummy_stream = os.pipe()
        self.dummy_content = sconf.get('dummy_content', 'aaaa')

    def dummy_invocation(self):
        os.write(self.dummy_stream[1], self.dummy_content)
        os.close(self.dummy_stream[1])
        return self.dummy_stream[0], {}

    def authorizeStorletExecution(self, request):
        return True

    def augmentStorletRequest(self, request):
        pass

    def gatewayProxyPutFlow(self, orig_request, container, obj):
        return self.dummy_invocation()

    def gatewayProxySloFlow(self, request, container, obj, original_response):
        return self.dummy_invocation()

    def gatewayObjectGetFlow(self, request, container, obj, original_response):
        return self.dummy_invocation()
