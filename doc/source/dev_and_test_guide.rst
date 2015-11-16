=======================
Development and Testing
=======================

This guide explains how to build the various components, and how to deploy them once built.
Note that some of the components being built need to be inserted to a docker image before
they can be tested. Thus, one should have an installed environment (see <https://github.com/openstack/storlets/blob/master/doc/source/installation.rst>)
before proceeding with the test and deploy steps (which are in fact a subset of the installation steps).

Building
========

The repo consists of code written in Python, Java and C. We have chose ant to serve as a 'make' tool for all code.
The main build task in build.xml is dependent on two other build tasks:

#. build_storlets task, used above. This task builds all the sample storlets used in the system tests.
#. build engine task, used for building/packaging the following components:

  #. The storlet middleware and the storlet docker gateway python code. These are build as two packages in a single 'storlets' egg:

    * storlet_middleware
    * storlet_gateway

  #. The SBus code. This is the communication module between the gateway and the Docker container. It has a transport layer written in "C" and 
     'bindings' to both Java and Python.
  #. The Python written storlet_factory_daemon, which is packaged for installation in a Docker image
  #. The Java SDaemon code, which is the daemon code that loads the Storlets in run time. This code is compiled to a .jar that is later installed
     in the Docker image.
  #. The Java SCommon code, which has the Storlet interface declaration, as well as the accompanying classes appearing in the interface. This code
     is copiled to a .jar that is required both in the Docker image as well as for building Storlets.

Deploying
=========

Two additional tasks of interest in our build.xml are the deploy_host_engine and deploy_container_engine. These tasks are based on the Ansible installation scripts and do the following:

#. deploy_host_engine would get all the code that is relevant to the host side (python middleware and SBus) and deploy it on the hosts, as described in Deploy/playbook/hosts file
#. deploy_container_engine, would create an updated image of the tenant defined in Deploy/playbook/common.yml and distribute it to all nodes as defined in Deploy/playbook/hosts. Typically, the hosts file will describe an all-in-one type of installation.

Running the Tests
=================

Other than testing, those tests are a good reference for writing and deploying storlets.
To run the system tests follow the next steps:

#. cd to the repo root
#. run 'ant build_storlets'
#. cd to SystemTests
#. Edit the file sys_test_params.py and make sure that the following variables match the installation.
   If you have used the storlets all-in-one installation, this is already taken care of.

  - DEV_AUTH_IP - The IP of the Keystone authentication endpoint 
  - ACCOUNT - The name of the account created for Storlets
  - USER_NAME - The user name created for the account 
  - PASSWORD = The above user password

#. run 'python sys_test.py'

