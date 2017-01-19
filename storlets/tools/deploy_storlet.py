# Copyright IBM Corp. 2015, 2015 All Rights Reserved
# Copyright (c) 2010-2016 OpenStack Foundation
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

import sys
import zipfile
from storlets.tools.cluster_config_parser import ClusterConfig
from storlets.tools.utils import get_auth, deploy_storlet

CLS_SUFFIX = '.class'


class StdinReader(object):
    """
    Helper reader class to get stdin and map the value to specified key

    :param key: a string but it's never used in this class just a reference
                for the value should be assigned
    :param run_once: bool. If set False, continue to readline until blank line
                     in __call__ method.
    :param callback: function which should be called with the value after
                     all lines were read.
    """
    def __init__(self, key, run_once=True, callback=None):
        self.key = key
        self.run_once = run_once
        self.callback = callback

    def __call__(self):
        """
        :return: string when run_once == True else list
        """
        line = sys.stdin.readline().rstrip()
        if not self.run_once:
            value = []
            while line:
                value.append(line)
                line = sys.stdin.readline().rstrip()
        else:
            value = line

        if self.callback:
            self.callback(value)

        return value


def list_classes(storlet_file):
    print("Your jar file contains the following classes:")
    with zipfile.ZipFile(storlet_file, 'r') as zfile:
        for f in zfile.infolist():
            name = f.filename
            if name.endswith(CLS_SUFFIX):
                print('\t* ' +
                      name[:-len(CLS_SUFFIX)].replace('/', '.'))


MESSAGES = {
    'Java': iter([
        ("Enter absolute path to storlet jar file: ",
         StdinReader("storlet", callback=list_classes)),
        ("Please enter fully qualified storlet main class "
         "(choose from the list above): ", StdinReader("storlet_main_class")),
        ("Please enter dependency files "
         "(leave a blank line when you are done):",
         StdinReader("dependencies", False))]),
    'Python': iter([
        ("Enter absolute path to storlet file: ", StdinReader("storlet")),
        ("Please enter fully qualified storlet main class "
         "<filename.ClassName>: ", StdinReader("storlet_main_class")),
        ("Please enter dependency files "
         "(leave a blank line when you are done): ",
         StdinReader("dependencies", False))]),
}


def usage():
    print("Useage: deploy_storlet.py <path to conf>")


def main(argv):
    if len(argv) != 1:
        usage()
        return 1
    conf = ClusterConfig(argv[0])
    url, token = get_auth(conf, conf.admin_user, conf.admin_password)
    print("Enter storlet language (java or python): ")
    storlet_language = sys.stdin.readline().rstrip().title()

    if storlet_language not in MESSAGES:
        print("The language you specified is not supported")
        return 1

    message_iter = MESSAGES[storlet_language]
    options_dict = dict(language=storlet_language)
    for message, reader in message_iter:
        print(message)
        options_dict[reader.key] = reader()

    deploy_storlet(url, token, **options_dict)

    print("Storlet deployment complete")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
