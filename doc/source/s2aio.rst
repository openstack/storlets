=====
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

    ./s2aio dev docker

If you do not have Docker installed on your host, the above script
will install it and set docker to use "vfs" as the docker storage driver
which typically is aufs. If you have Docker installed you must change its
storage driver to "vfs". The created Docker container runs yet another
container. Running Docker in Docker requires the usage of the "vfs" storage
device.
