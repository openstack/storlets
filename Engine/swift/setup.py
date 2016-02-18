"""-------------------------------------------------------------------------
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
-------------------------------------------------------------------------"""
from setuptools import setup
paste_factory = ['storlet_handler = '
                 'storlet_middleware.storlet_handler:filter_factory']

setup(name='storlets',
      version='1.0',
      packages=['storlet_middleware', 'storlet_gateway'],
      entry_points={'paste.filter_factory': paste_factory}
      )
