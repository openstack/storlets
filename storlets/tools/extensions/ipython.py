# Copyright (c) 2015, 2016 OpenStack Foundation.
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


"""Implementation of magic funcs for interaction with the OpenStack Storlets.

This extension is desined to use os environment variables to set
authentication and storage target host. (for now)

"""
from __future__ import print_function

import os
from swiftclient.client import Connection

from IPython.core import magic_arguments
# TODO(kota_): we may need some error handing in ipython shell so keep those
#              errors import as references.
# from IPython.core.alias import AliasError, Alias
from IPython.core.error import UsageError
from IPython.core.magic import Magics, magics_class, cell_magic
from IPython.utils.py3compat import unicode_type


def get_swift_connection():
    # find api version
    for k in ('ST_AUTH_VERSION', 'OS_AUTH_VERSION', 'OS_IDENTITY_API_VERSION'):
        if k in os.environ:
            auth_version = os.environ[k]
            break
    else:
        auth_version = 1

    # cast from string to int
    auth_version = int(float(auth_version))

    if auth_version == 3:
        # keystone v3
        try:
            auth_url = os.environ['OS_AUTH_URL']
            auth_user = os.environ['OS_USERNAME']
            auth_password = os.environ['OS_PASSWORD']
            project_name = os.environ['OS_PROJECT_NAME'],
        except KeyError:
            raise UsageError(
                "You need to set OS_AUTH_URL, OS_USERNAME, OS_PASSWORD and "
                "OS_PROJECT_NAME for Swift authentication")
        auth_os_options = {
            'user_domain_name': os.environ.get(
                'OS_USER_DOMAIN_NAME', 'Default'),
            'project_domain_name': os.environ.get(
                'OS_PROJECT_DOMAIN_NAME', 'Default'),
            'project_name': project_name,
        }
        return Connection(auth_url, auth_user, auth_password,
                          os_options=auth_os_options,
                          auth_version='3')

    elif auth_version == 2:
        # keystone v2 (not implemented)
        raise NotImplementedError('keystone v2 is not supported')
    else:
        try:
            auth_url = os.environ['ST_AUTH']
            auth_user = os.environ['ST_USER']
            auth_password = os.environ['ST_KEY']
        except KeyError:
            raise UsageError(
                "You need to set ST_AUTH, ST_USER, ST_KEY for "
                "Swift authentication")
        return Connection(auth_url, auth_user, auth_password)


@magics_class
class StorletMagics(Magics):
    """Magics to interact with OpenStack Storlets
    """

    @magic_arguments.magic_arguments()
    @magic_arguments.argument(
        'container_obj', type=unicode_type,
        help='container/object path to upload'
    )
    @cell_magic
    def uploadfile(self, line, cell):
        """Upload the contents of the cell to OpenStack Swift.
        """
        args = magic_arguments.parse_argstring(self.uploadfile, line)
        container, obj = args.container_obj.split('/', 1)
        conn = get_swift_connection()
        conn.put_object(container, obj, cell,
                        {'Content-Type': 'application/python'})

    @magic_arguments.magic_arguments()
    @magic_arguments.argument(
        'module_class', type=unicode_type,
        help='module and class name to upload'
    )
    @magic_arguments.argument(
        '-c', '--container', type=unicode_type, default='storlet',
        help='Storlet container name, "storlet" in default'
    )
    @magic_arguments.argument(
        '-d', '--dependencies', type=unicode_type, default='storlet',
        help='Storlet container name, "storlet" in default'
    )
    @magic_arguments.argument(
        '--with-invoke', action='store_true', default=False,
        help='An option to run storlet for testing. '
             'This requires --input option'
    )
    @magic_arguments.argument(
        '--input', type=unicode_type, default='',
        help='Specifiy input object path that must be of the form '
             '"path:/<container>/<object>"'
    )
    @magic_arguments.argument(
        '--print-result', action='store_true', default=False,
        help='Print result objet to stdout. Note that this may be a large'
             'binary depends on your app'
    )
    @cell_magic
    def storletapp(self, line, cell):
        args = magic_arguments.parse_argstring(self.storletapp, line)
        module_path = args.module_class
        assert module_path.count('.') == 1
        headers = {
            'X-Object-Meta-Storlet-Language': 'python',
            'X-Object-Meta-Storlet-Interface-Version': '1.0',
            'X-Object-Meta-Storlet-Object-Metadata': 'no',
            'X-Object-Meta-Storlet-Main': module_path,
            'Content-Type': 'application/octet-stream',
        }
        storlet_obj = '%s.py' % module_path.split('.')[0]

        conn = get_swift_connection()
        conn.put_object(args.container, storlet_obj, cell, headers=headers)

        print('Upload storlets succeeded /%s/%s'
              % (args.container, storlet_obj))
        print('Example command `swift download <container> <object> '
              '-H X-Run-Storlet:%s`' % storlet_obj)

        if args.with_invoke:
            if not args.input:
                raise UsageError(
                    '--with-invoke option requires --input to run the app')
            if not args.input.startswith('path:'):
                raise UsageError(
                    '--input option for --with-invoke must be path format '
                    '"path:/<container>/<object>"')
            try:
                src_container_obj = args.input[len('path:'):]
                src_container, src_obj = src_container_obj.strip(
                    '/').split('/', 1)
            except ValueError:
                raise UsageError(
                    '--input option for --with-invoke must be path format '
                    '"path:/<container>/<object>"')

            headers = {'X-Run-Storlet': '%s' % storlet_obj}

            # invoke storlet app
            resp_headers, resp_content_iter = conn.get_object(
                src_container, src_obj, resp_chunk_size=64 * 1024,
                headers=headers)

            print('Invocation Complete')
            if args.print_result:
                print('Result Content:')
                print(''.join(resp_content_iter))
            else:
                # drain all resp content stream
                for x in resp_content_iter:
                    pass


def load_ipython_extension(ipython):
    ipython.register_magics(StorletMagics)
