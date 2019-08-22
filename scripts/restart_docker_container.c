/*----------------------------------------------------------------------------
 * Copyright IBM Corp. 2015, 2015 All Rights Reserved
 * Copyright (c) 2010-2016 OpenStack Foundation
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * Limitations under the License.
 * ---------------------------------------------------------------------------
*/

#define _GNU_SOURCE
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <sys/types.h>

 /*
  * Stop and Run a docker container using:
  * docker stop <container name>
  * docker run --name <container name> -d -v /dev/log:/dev/log -v <mount dir 1> -v <mount dir 2> -i -t <image> --net='none'
  * <container name> - The name of the container to stop / to start
  * <image name> - the name of the image from which to start the container
  * <mount dir 1> - The directory where the named pipes are placed. Typically mounted to /mnt/channels in the container
  * <mount dir 2> - The directory where the storlets are placed. Typically mounted to /home/swift in the container
  */

int main(int argc, char **argv) {
    char command[4096];
    char container_name[256];
    char container_image[256];
    char mount_dir1[512];
    char mount_dir2[512];
    char mount_dir3[512];
    char mount_dir4[512];
    char mount_dir5[512];

    if (argc != 8) {
        fprintf(stderr, "Usage: %s container_name container_image mount_dir1 mount_dir2 mount_dir3 mount_dir4\n",
            argv[0]);
        return 1;
    }

    snprintf(container_name,(size_t)256,"%s",argv[1]);
    snprintf(container_image,(size_t)256,"%s",argv[2]);
    snprintf(mount_dir1,(size_t)512, "%s", argv[3]);
    snprintf(mount_dir2,(size_t)512, "%s", argv[4]);
    snprintf(mount_dir3,(size_t)512, "%s", argv[5]);
    snprintf(mount_dir4,(size_t)512, "%s", argv[6]);
    snprintf(mount_dir5,(size_t)512, "%s", argv[7]);

    int ret;
    setresuid(0, 0, 0);
    setresgid(0, 0, 0);
    sprintf(command, "/usr/bin/docker stop -t 1 %s", container_name);
    ret = system(command);

    sprintf(command, "/usr/bin/docker rm %s", container_name);
    ret = system(command);

    sprintf(command,
            "/usr/bin/docker run --net=none --name %s -d -v /dev/log:/dev/log -v %s -v %s -v %s -v %s -v %s -i -t %s",
            container_name,
            mount_dir1,
            mount_dir2,
            mount_dir3,
            mount_dir4,
            mount_dir5,
            container_image);
    ret = system(command);
    if(ret){
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
