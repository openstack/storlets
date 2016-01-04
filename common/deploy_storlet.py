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

import os
import sys
import zipfile
from cluster_config_parser import ClusterConfig
from utils import storlet_get_auth, deploy_storlet


def list_classes(storlet_jar):
    z = zipfile.ZipFile(storlet_jar, 'r')
    for f in z.infolist():
        name = f.filename
        if name.endswith(".class"):
            print('\t* ' + name[0:len(name) - 6].replace('/', '.'))
    z.close()


def usage():
    print("Useage: deploy_storlet.py <path to conf>")


def main():
    if len(sys.argv) != 2:
        usage()
        sys.exit(-1)
    conf = ClusterConfig(sys.argv[1]).get_conf()
    url, token = storlet_get_auth(conf)
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
    dependencies = []
    dependency_jar = sys.stdin.readline().rstrip()
    while dependency_jar:
        dependency_jars.append(dependency_jar)
        dependencies.append(os.path.basename(dependency_jar))
        dependency_jar = sys.stdin.readline().rstrip()

    deploy_storlet(url, token, storlet_jar, storlet_main_class,
                   dependency_jars, dependencies)

if __name__ == "__main__":
    main()
