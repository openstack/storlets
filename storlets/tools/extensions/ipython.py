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
import string
from swiftclient.client import Connection

from IPython.core import magic_arguments
# TODO(kota_): we may need some error handing in ipython shell so keep those
#              errors import as references.
# from IPython.core.alias import AliasError, Alias
from IPython.core.error import UsageError
from IPython.core.magic import Magics, magics_class, cell_magic, line_magic
from IPython.utils.py3compat import unicode_type


class Response(object):
    """
    Response object to return the object to ipython cell

    :param status: int for status code
    :param headers: a dict for repsonse headers
    :param body_iter: an iterator object which takes the body content from
    """
    def __init__(self, status, headers, body_iter=None):
        self.status = status
        self.headers = headers
        self._body_iter = body_iter or iter([])

    def __iter__(self):
        print('hoge')
        return self._body_iter

    def iter_content(self):
        # TODO(kota_): supports chunk_size like requests.Response
        return self._body_iter

    @property
    def content(self):
        return ''.join([chunk for chunk in self._body_iter])


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
            project_name = os.environ['OS_PROJECT_NAME']
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

    def _parse_input_path(self, path_str):
        """
        Parse formatted to path to swift container and object names

        :param path_str: path string starts with "path:" prefix
        :return (container, obj): Both container and obj are formatted
            as string
        :raise UsageError: if the path_str is not formatted as expected
        """
        if not path_str.startswith('path:'):
            raise UsageError(
                'swift object path must have the format: '
                '"path:/<container>/<object>"')
        try:
            src_container_obj = path_str[len('path:'):]
            src_container, src_obj = src_container_obj.strip(
                '/').split('/', 1)
            return src_container, src_obj
        except ValueError:
            raise UsageError(
                'swift object path must have the format: '
                '"path:/<container>/<object>"')

    def _generate_params_headers(self, param_dict):
        """
        Parse parameter args dict to swift headers

        :param param_dict: a dict of input parameters
        :return headers: a dict for swift headers
        """
        headers = {}
        for i, (key, value) in enumerate(param_dict.items()):
            headers['X-Storlet-Parameter-%d' % i] =\
                '%s:%s' % (key, value)

        return headers

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

            src_container, src_obj = self._parse_input_path(args.input)

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

    @magic_arguments.magic_arguments()
    @magic_arguments.argument(
        '--input', type=unicode_type,
        help='The input object for the storlet execution'
             'this option must be of the form "path:<container>/<object>"'
    )
    @magic_arguments.argument(
        '--storlet', type=unicode_type,
        help='The storlet to execute over the input'
    )
    @magic_arguments.argument(
        '-i', type=unicode_type,
        help=('A name of a variable defined in the environment '
              'holding a dictionary with the storlet invocation '
              'input parameters')
    )
    @magic_arguments.argument(
        '-o', type=unicode_type,
        help=('A name of an output variable to hold the invocation result '
              'The output variable is a dictionary with the fields: '
              'status, headers, content_iter holding the response status, '
              'headers, and body iterator accordingly')
    )
    @line_magic
    def get(self, line):
        args = magic_arguments.parse_argstring(self.get, line)
        if not args.o:
            raise UsageError('-o option is mandatory for the invocation')
        if not args.o[0].startswith(tuple(string.ascii_letters)):
            raise UsageError('The output variable name must be a valid prefix '
                             'of a python variable, that is, start with a '
                             'letter')
        if not args.storlet:
            raise UsageError('--storlet option is mandatory '
                             'for the invocation')
        if not args.input:
            raise UsageError('--input option is mandatory for the invocation')

        src_container, src_obj = self._parse_input_path(args.input)

        headers = {'X-Run-Storlet': '%s' % args.storlet}
        # pick -i option and translate the params to
        # X-Storlet-Parameter-x headers
        storlet_headers = self._generate_params_headers(
            self.shell.user_ns[args.i] if args.i else {})
        headers.update(storlet_headers)

        # invoke storlet app on get
        conn = get_swift_connection()
        response_dict = dict()
        resp_headers, resp_content_iter = conn.get_object(
            src_container, src_obj,
            resp_chunk_size=64 * 1024,
            headers=headers,
            response_dict=response_dict)

        res = Response(int(response_dict['status']),
                       resp_headers,
                       resp_content_iter)
        self.shell.user_ns[args.o] = res

    @magic_arguments.magic_arguments()
    @magic_arguments.argument(
        '--input', type=unicode_type,
        help='The input object for the storlet execution'
             'this option must be of the form "path:<container>/<object>"'
    )
    @magic_arguments.argument(
        '--output', type=unicode_type,
        help='The output object for the storlet execution'
             'this option must be of the form "path:<container>/<object>"'
    )
    @magic_arguments.argument(
        '--storlet', type=unicode_type,
        help='The storlet to execute over the input'
    )
    @magic_arguments.argument(
        '-i', type=unicode_type,
        help=('A name of a variable defined in the environment '
              'holding a dictionary with the storlet invocation '
              'input parameters')
    )
    @magic_arguments.argument(
        '-o', type=unicode_type,
        help=('A name of an output variable to hold the invocation result '
              'The output variable is a dictionary with the fields: '
              'status, headers, holding the response status and '
              'headers accordingly')
    )
    @line_magic
    def copy(self, line):
        args = magic_arguments.parse_argstring(self.copy, line)
        if not args.o:
            raise UsageError('-o option is mandatory for the invocation')
        if not args.o[0].startswith(tuple(string.ascii_letters)):
            raise UsageError('The output variable name must be a valid prefix '
                             'of a python variable, that is, start with a '
                             'letter')
        if not args.storlet:
            raise UsageError('--storlet option is mandatory '
                             'for the invocation')
        if not args.input:
            raise UsageError('--input option is mandatory for the invocation')

        if not args.output:
            raise UsageError('--output option is mandatory for the invocation')

        src_container, src_obj = self._parse_input_path(args.input)
        dst_container, dst_obj = self._parse_input_path(args.output)
        destination = '/%s/%s' % (dst_container, dst_obj)

        headers = {'X-Run-Storlet': '%s' % args.storlet}
        # pick -i option and translate the params to
        # X-Storlet-Parameter-x headers
        storlet_headers = self._generate_params_headers(
            self.shell.user_ns[args.i] if args.i else {})
        headers.update(storlet_headers)

        # invoke storlet app on copy
        conn = get_swift_connection()

        response_dict = dict()
        conn.copy_object(
            src_container, src_obj,
            destination=destination,
            headers=headers,
            response_dict=response_dict)

        res = Response(int(response_dict['status']),
                       response_dict['headers'])
        self.shell.user_ns[args.o] = res

    @magic_arguments.magic_arguments()
    @magic_arguments.argument(
        '--input', type=unicode_type,
        help='The local input object for upload'
             'this option must be a full path of a local file'
    )
    @magic_arguments.argument(
        '--output', type=unicode_type,
        help='The  output object of the storlet execution'
             'this option must be of the form "path:<container>/<object>"'
    )
    @magic_arguments.argument(
        '--storlet', type=unicode_type,
        help='The storlet to execute over the input'
    )
    @magic_arguments.argument(
        '-i', type=unicode_type,
        help=('A name of a variable defined in the environment '
              'holding a dictionary with the storlet invocation '
              'input parameters')
    )
    @magic_arguments.argument(
        '-o', type=unicode_type,
        help=('A name of an output variable to hold the invocation result '
              'The output variable is a dictionary with the fields: '
              'status, headers, holding the response status and '
              'headers accordingly')
    )
    @line_magic
    def put(self, line):
        args = magic_arguments.parse_argstring(self.put, line)
        if not args.o:
            raise UsageError('-o option is mandatory for the invocation')
        if not args.o[0].startswith(tuple(string.ascii_letters)):
            raise UsageError('The output variable name must be a valid prefix '
                             'of a python variable, that is, start with a '
                             'letter')
        if not args.storlet:
            raise UsageError('--storlet option is mandatory '
                             'for the invocation')
        if not args.input:
            raise UsageError('--input option is mandatory for the invocation')
        if not args.input.startswith('/'):
            raise UsageError('--input argument must be a full path')

        if not args.output:
            raise UsageError('--output option is mandatory for the invocation')

        dst_container, dst_obj = self._parse_input_path(args.output)

        headers = {'X-Run-Storlet': '%s' % args.storlet}
        # pick -i option and translate the params to
        # X-Storlet-Parameter-x headers
        storlet_headers = self._generate_params_headers(
            self.shell.user_ns[args.i] if args.i else {})
        headers.update(storlet_headers)

        # invoke storlet app on copy
        conn = get_swift_connection()
        response_dict = dict()
        with open(args.input, 'r') as content:
            conn.put_object(
                dst_container, dst_obj,
                content,
                headers=headers,
                response_dict=response_dict)

        res = Response(int(response_dict['status']),
                       response_dict['headers'])
        self.shell.user_ns[args.o] = res


def load_ipython_extension(ipython):
    ipython.register_magics(StorletMagics)
