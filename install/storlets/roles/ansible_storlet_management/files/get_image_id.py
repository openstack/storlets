#!/usr/bin/python

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

import json
import subprocess
import sys


def extractId(tar_file_name, repository, tag):
    subprocess.call(['tar', 'xf', tar_file_name, 'repositories'])
    repository_file = open('repositories')
    j = json.loads(repository_file.read())

    if repository not in j:
        print("Not Found")
    else:
        pairs = j[repository]
        if tag:
            if tag not in pairs:
                print("Not Found")
            else:
                print(pairs[tag])
        else:
            if len(pairs) != 1:
                print("No tag supplied. Ambiguous")
            else:
                print(pairs.values()[0])

    repository_file.close()
    subprocess.call(['rm', '-f', 'repositories'])


def usage(argv):
    print(argv[0] + " <tar_file> <repository> [tag]")


def main(argv):
    if len(argv) < 3 or len(argv) > 4:
        usage(argv)
        return

    tar_file_name = argv[1]
    repository = argv[2]
    tag = None
    if len(argv) >= 4:
        tag = argv[3]

    extractId(tar_file_name, repository, tag)

if __name__ == "__main__":
    main(sys.argv)
