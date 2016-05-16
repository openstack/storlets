=============================
Development and Testing Guide
=============================

This guide explains how to build the various components, and how to deploy them once built.
Note that some of the components being built need to be inserted to a docker image before
they can be tested. Thus, one should have an installed environment as described in
the development environment installation instructions_ or in the getting started guide_

.. _instructions: engine_dev_installation.html
.. _guide: getting_started.html

--------
Building
--------
The storlets repository consists of code written in Python, Java and C. We have chose ant to serve as a 'make' tool for all of the code.
The main build task in build.xml is dependent on two other build tasks:

#. build_storlets task. This task builds all the sample storlets used in the system tests.
#. build engine task. This task  builds/packages the following components:

  #. The storlet middleware and the "storlet docker gateway" python code. These are built as two packages in a single 'storlets' egg:

    * storlet_middleware
    * storlet_gateway

  #. The SBus code. This is the communication module between the gateway and the Docker container. It has a transport layer written in "C" with 
     'bindings' to both Java and Python.
  #. The Python written storlet_factory_daemon, which is packaged for installation in a Docker image
  #. The Java SDaemon code, which is the daemon code that loads the storlets in run time. This code is compiled to a .jar that is later installed
     in the Docker image.
  #. The Java SCommon code, which has the storlet interface declaration, as well as the accompanying classes appearing in the interface. This code
     is compiled to a .jar that is required both in the Docker image as well as for building storlets.

---------
Deploying
---------
Two additional tasks of interest in our build.xml are the deploy_host_engine and deploy_container_engine.
These tasks are based on the Ansible installation scripts and do the following:

#. deploy_host_engine would get all the code that is relevant to the host side
   (python middleware and SBus) and deploy it on the hosts as descrined in the 
   cluster_config.json file
#. deploy_container_engine, would create an updated image of the tenant defined
   in the cluster_config.json and distribute it to all nodes as defined in 
   the configuration.

-----------------
Running the Tests
-----------------

Unit tests
----------

Unit tests can be invoked using:

::

    ./.unittests

from the repo root.


Functional tests
----------------

The functional tests can be invoked using:

::

    ./.functests

from the repo root.

.. note::

  Other than testing, those tests are a good reference for writing and deploying storlets.
