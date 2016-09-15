# Copyright (c) 2010-2015 OpenStack Foundation
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
from swift.common.swob import Request, HeaderKeyDict


class FakeApp(object):

    def __init__(self):
        self._calls = []
        self._responses = {}

    def __call__(self, env, start_response):
        req = Request(env)

        # Get request parameters
        req_method = req.method
        req_path = req.path
        req_headers = req.headers
        req_body = req.body
        self._calls.append((req_method, req_path, req_headers, req_body))
        try:
            resp_cls, raw_headers, body = \
                self._responses[(req_method, req_path)]
            headers = HeaderKeyDict(raw_headers)
        except KeyError:
            if req_method == 'HEAD' and ('GET', req_path) in self._responses:
                resp_cls, raw_headers, _ = self._responses[('GET', req_path)]
                body = None
                headers = HeaderKeyDict(raw_headers)
            else:
                raise
        resp = resp_cls(req=req, headers=headers, body=body,
                        conditional_response=True)
        return resp(env, start_response)

    def register(self, method, path, resp_cls, headers=None, body=None):
        self._responses[(method, path)] = (resp_cls, headers, body)

    def reset_responses(self):
        self._responses = {}

    def reset_calls(self):
        self._calls = []

    def reset_all(self):
        self.reset_responses()
        self.reset_calls()

    def call_count(self, method, path):
        return len(self.get_calls(method, path))

    def get_calls(self, method=None, path=None):
        if not method or not path:
            return self._calls
        else:
            return([(m, p, h, b) for (m, p, h, b) in self._calls
                   if m == method and p == path])
