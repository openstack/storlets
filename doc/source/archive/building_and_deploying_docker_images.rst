Introduction
============
The Swift account manager can supply a Docker image in which the account's storlets
are to be executed. When planning the Docker image, the account manager needs to consider the
following:

#. The image is built over an existing image that contains the storlets run time.
#. The image would be executed with no network devices, with limited memory and
   cpu.
#. A Docker image is not brought up as a general purpose Linux machine in terms
   of the init process. Specifically, do not install daemons that require special
   initializations on 'OS bring up'.

The idea is that a user supplied docker image would contain dependencies
required by storlets in the form of libraries.

Logical Flow
============
The flow of deploying an account manager tailored Docker image to Swift involves
both the account manager (customer side) and the Swift Storlet manager (provider side)
Below are the steps of this flow:

#. A prerequisite for the account manager to deploy a Docker image to Swift is having an
   account that is enabled for Storlets. This is an operation that is done by the Swift Storlet
   manager and is explained in <https://github.com/openstack/storlets/blob/master/doc/source/archive/storlets_management.rst>.
#. Once the account is enabled for Storlets, a container named docker_images is
   created, with access to both the account manager as well as the storlet manager.
   That container will include a basic Docker image consisting of some Storlet
   engine code that allows the Swift Storlet engine to work with that image.
#. The account manager can download this image, adjust it to his needs in terms of
   the installed software stack, and upload it back to the docker_images container.
#. Once uploaded, the account manager must notify the Swift Storlet engine manager
   of the update. The storlets manager would take care of testing and deploying
   it to all Swift nodes. Again, <https://github.com/openstack/storlets/blob/master/doc/source/archive/storlets_management.rst>
   describes the provided tool the Storlet manager can use for the actual deployment.

The sections below describe in detail the steps taken by the account manager.

Downloading the Docker Image
----------------------------
Downloading the Docker image involves a simple retrieval of a Swift object. To
get the exact name of the object just list the docker_images container in the
account. The name will carry the base OS system and engine language binding run
time. An example might be: ubuntu_14.04_jre8_storlets reflecting the following
facts:

#. The base OS is Ubuntu 14.04. Currently this is the only base OS we support.
#. The Storlets run time is jre8 and python2.7.
#. The storlet engine code is installed.

The image will come in a .tar format.

Below is an example of downloading the image from the tenant's docker_images
container using the swift CLI. As with all examples using the Swift CLI, we are
using environment variables defining the tenant, user credentials and auth URI.
All these are required for the operation of any Swift CLI. Please change them
accordingly.

.. code-block:: bash

  export OS_USERNAME=swift
  export OS_PASSWORD=passw0rd
  export OS_TENANT_NAME=service
  export OS_AUTH_URL=http://127.0.0.1:35357/v2.0

In the below we show:

#. Listing the docker_images container.
#. Downloading the image object
#. Getting the image object's metadata. Pay attention to the image_name metadata
   field of the object. It is required for the next steps.

::

   eranr@lnx-ccs8:~$ swift list docker_images
   ubuntu_14.04_jre8_storlets.tar
   eranr@lnx-ccs8:~$ swift download docker_images ubuntu_14.04_jre8_storlets.tar
   ubuntu_14.04_jre8_storlets.tar [headers 0.311s, total 8.550s, 68.008 MB/s]
   eranr@lnx-ccs8:~$ swift stat docker_images ubuntu_14.04_jre8_storlets.tar
          Account: AUTH_305f5f3d12834be187238e080b8643e4
        Container: docker_images
           Object: ubuntu_14.04_jre8_storlets.tar
     Content Type: application/x-tar
   Content Length: 581439488
    Last Modified: Sat, 25 Oct 2014 19:47:13 GMT
             ETag: ac014db984be37faf7307801baa11ab0
  Meta Image-Name: ubuntu_14.04_jre8_storlets
       Meta Mtime: 1414266426.880534
    Accept-Ranges: bytes
      X-Timestamp: 1414266432.09929
       X-Trans-Id: tx794e21cd40b544e6a377b-00544bfed3

Tuning the Docker Image
-----------------------
To tune the Docker image, Docker must be used. To install please refer to
https://docs.docker.com/install/

The below steps illustrate the tuning process:

1. Use docker load to load the .tar image. Each Docker client maintains a local
   repository of the images from which containers can be executed. The load
   operation simply loads the .tar file to that local repository. Note that once
   the .tar is loaded, the docker images command shows the image, whose name has
   a suffix identical to the image object Swift metadata.

  ::

    root@lnx-ccs8:/home/eranr# docker load -i ubuntu_14.04_jre8_storlets.tar
    root@lnx-ccs8:/home/eranr# docker images
    REPOSITORY                                  TAG                 IMAGE ID        CREATED             VIRTUAL SIZE
    localhost:5001/ubuntu_14.04_jre8_storlets   latest              f6929e6abc60    3 days ago          563.6 MB

2. Use a Docker file that is based on the loaded image to make the necessary
   changes to the image. Below is a Dockerfile for installing 'ffmpeg'. Few
   notes are in place:

   #. The first line "FROM" must carry the image name we have downloaded.
   #. The maintainer needs to be a user that is allowed to do the actual actions
      within the container. Please leave it as is.
   #. The below example shows ffmpeg installation. For more options and
       information on Dockerfiles, please refer to:
       https://docs.docker.com/engine/reference/builder/
   #. One MUST refrain from using the Dockerfile ENTRYPOINT and CMD. Using those
      will cause the image from being unusable by the Storlet engine.

  ::

    root@lnx-ccs8:/home/eranr/dockerfile_example# cat Dockerfile
    FROM 127.0.0.1:5001/ubuntu_14.04_jre8_storlets
 
    MAINTAINER root

    RUN ["apt-get", "update"]
    RUN ["apt-get", "install","-y", "software-properties-common"]
    RUN ["add-apt-repository","deb http://ppa.launchpad.net/jon-severinsson/ffmpeg/ubuntu trusty main"]
    RUN ["apt-key", "adv", "--recv-keys", "--keyserver", "keyserver.ubuntu.com", "1DB8ADC1CFCA9579"]
    RUN ["apt-key", "update"]
    RUN ["apt-get", "update"]
    RUN ["apt-get", "install", "-y", "ffmpeg"]

3. We now use the Docker fie to create a new image from it. Note the -t directive
   for the new image name to be created. The name of the image would be required
   for the Storlet manager to deploy the Storlet. Also, note that the command
   ends with a dot "." specifying in which directory the build is taking place.
   when building an image that copies stuff into the image, all that stuff must
   reside in that building directory.

.. code-block:: bash

    root@lnx-ccs8:/home/eranr/dockerfile_example# docker build -t service_tenant_image .
    Sending build context to Docker daemon 2.56 kB
    Sending build context to Docker daemon
    Step 0 : FROM 127.0.0.1:5001/ubuntu_14.04_jre8_storlets
    ---> f6929e6abc60
    ......
    Processing triggers for libc-bin (2.19-0ubuntu6.3) ...
    ---> 11975468ecf8
    Removing intermediate container 226d2510b925
    Successfully built 11975468ecf8

4. At this point listing the images, shows the newly created image.

  ::

    root@lnx-ccs8:/home/eranr/dockerfile_example# docker images
    REPOSITORY                                  TAG                 IMAGE ID            CREATED             VIRTUAL SIZE
    service_tenant_image                        latest              11975468ecf8        7 minutes ago       660.1 MB
    localhost:5001/ubuntu_14.04_jre8_storlets   latest              f6929e6abc60        4 days ago          563.6 MB

Currently, we have no testing tool that can actually test a storlet inside the
created image. The best one can do is run a Docker container based on the
image, and run within it code that simulates how the Storlet would use the image.
Below we run /bin/bash inside a container based on the newly created image.
We then invoke ffmpeg showing that the installation was indeed successful.
Note that the 'debug' parameter tells our entry point not to execute the storlet
engine but rather the /bin/bash from which we can run ffmpeg

.. code-block:: bash

  root@lnx-ccs8:/home/eranr/dockerfile_example# docker run -i -t service_tenant_image debug /bin/bash
  root@b129c3e6e76b:/# ffmpeg
  ffmpeg version 1.2.6-7:1.2.6-1~trusty1 Copyright (c) 2000-2014 the FFmpeg developers
    built on Apr 26 2014 18:52:58 with gcc 4.8 (Ubuntu 4.8.2-19ubuntu1)
    configuration: --arch=amd64 --disable-stripping --enable-avresample --enable-pthreads --enable-runtime-cpudetect --extra-version='7:1.2.6-1~trusty1' --libdir=/usr/lib/x86_64-linux-gnu --prefix=/usr --enable-bzlib --enable-libdc1394 --enable-libfreetype --enable-frei0r --enable-gnutls --enable-libgsm --enable-libmp3lame --enable-librtmp --enable-libopencv --enable-libopenjpeg --enable-libopus --enable-libpulse --enable-libschroedinger --enable-libspeex --enable-libtheora --enable-vaapi --enable-vdpau --enable-libvorbis --enable-libvpx --enable-zlib --enable-gpl --enable-postproc --enable-libcdio --enable-x11grab --enable-libx264 --shlibdir=/usr/lib/x86_64-linux-gnu --enable-shared --disable-static
    libavutil      52. 18.100 / 52. 18.100
    libavcodec     54. 92.100 / 54. 92.100
    libavformat    54. 63.104 / 54. 63.104
    libavdevice    53.  5.103 / 53.  5.103
    libavfilter     3. 42.103 /  3. 42.103
    libswscale      2.  2.100 /  2.  2.100
    libswresample   0. 17.102 /  0. 17.102
    libpostproc    52.  2.100 / 52.  2.100
  Hyper fast Audio and Video encoder
  usage: ffmpeg [options] [[infile options] -i infile]... {[outfile options] outfile}...

  Use -h to get full help or, even better, run 'man ffmpeg'


Uploading the Docker Image
--------------------------
1. Use docker save to save the image as a tar file:

.. code-block:: bash

  root@lnx-ccs8:/home/eranr/dockerfile_example# docker save -o service_tenant_image.tar service_tenant_image

2. Again, we use the Swift CLI to upload the image. We assume the appropriate
   environment variables are in place.

.. code-block:: bash

  root@lnx-ccs8:/home/eranr/dockerfile_example# swift upload docker_images service_tenant_image.tar
  service_tenant_image.tar
