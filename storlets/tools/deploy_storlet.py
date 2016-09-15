'''-------------------------------------------------------------------------
Copyright IBM Corp. 2015, 2016 All Rights Reserved
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
import sys
import zipfile
from storlets.tools.cluster_config_parser import ClusterConfig
from storlets.tools.utils import get_auth, deploy_storlet

CLS_SUFFIX = '.class'


def list_classes(storlet_jar):
    with zipfile.ZipFile(storlet_jar, 'r') as zfile:
        for f in zfile.infolist():
            name = f.filename
            if name.endswith(CLS_SUFFIX):
                print('\t* ' +
                      name[:-len(CLS_SUFFIX)].replace('/', '.'))


def usage():
    print("Useage: deploy_storlet.py <path to conf>")


def main(argv):
    if len(argv) != 1:
        usage()
        return -1
    conf = ClusterConfig(argv[0])
    url, token = get_auth(conf, conf.admin_user, conf.admin_password)
    sys.stdout.write("Enter absolute path to storlet jar file: ")
    storlet_jar = sys.stdin.readline().rstrip()
    print("Your jar file contains the following classes:")
    list_classes(storlet_jar)
    sys.stdout.write("Please enter fully qualified storlet main class " +
                     "(choose from the list above): ")
    storlet_main_class = sys.stdin.readline().rstrip()
    print("Please enter dependency jars (leave a blank line when you are "
          "done):")
    dependency_jars = []
    dependency_jar = sys.stdin.readline().rstrip()
    while dependency_jar:
        dependency_jars.append(dependency_jar)
        dependency_jar = sys.stdin.readline().rstrip()

    deploy_storlet(url, token, storlet_jar, storlet_main_class,
                   dependency_jars)
    print("Storlet deployment complete")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
