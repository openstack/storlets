s2aio
=====

s2aio is a script that installs Swift and Storlets all on one.
The script allows to do the installation either on the host
where it is invoked or in a Docker container.

To install on the host:

.. include:: s2aio_dev_host_include.rst

To install in a Docker container follow the same steps,
replacing the last command with:

::

    ./s2aio.sh install dev docker

If you do not have Docker installed on your host, the above script
will install it and set docker to use "vfs" as the docker storage driver
(instead of the default "aufs" storage driver). If you already have
Docker installed, you may need to change its
storage driver to "vfs". The created Docker container runs yet another
container. Running Docker in Docker may require the usage of the "vfs" storage
device.

When installed on the host, the script can be used to start and stop all
relevant services using:

::

    ./s2aio.sh stop

and

::

    ./s2aio.sh start

For the Swift data, the s2aio installation uses a loopback device over a .img file.
When shutting down the host, the .img file may get corrupted. Thus, the above stop and
start commands are useful when using s2aio.sh for in a long lived hosts that can get rebooted
from time to time.
