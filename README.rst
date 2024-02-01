Storlets
========

Storlets extend Swift with the ability to run user defined computations
- called storlets - near the data in a secure and isolated manner.
A storlet is a compiled and packaged code (e.g. a .jar file) that can be
uploaded to Swift as any other object.
Once uploaded the storlet can be invoked over data objects in Swift.
The Storlets API is documented at
`"Storlets API v1" <https://storlets.readthedocs.io/en/latest/api/overview_api.html>`__.

The project started off as an IBM research project, and was open sourced by IBM in 2014.

- The research leading to the development of this code received funding from the European Community's Seventh Framework Programme (FP7/2007-2013) under the grant agreements for the CASPAR, ENSURE and VISION Cloud projects.
- Various stages and different aspects of the development of this code received funding from the following European Community's Framework Programme:

  - Seventh Framework Programme (FP7/2007-2013) under the grant agreements for the ForgetIT project, where the code is used for offloading digital preservation functionalities to the storage.
  - Seventh Framework Programme (FP7/2007-2013) under the grant agreements for COSMOS project, where the code is used for analysis of IoT data.
  - Seventh Framework Programme (FP7/2007-2013) under the grant agreements for FI-CORE project where the code is integrated with a holistic cloud deployment solution, and from
  - Horizon 2020 (H2020/2014-2020) under the grant agreement for the IOStack project where the code is used as a backend implementing Storage policies and is used for analytics

Docs
----

The storlerts documentation is auto-generated after every commit and available
online at https://docs.openstack.org/storlets/latest/

Getting Started for Users
-------------------------

The fastest way to get started is
`"S2AIO - Swift Storlets All In One" <https://docs.openstack.org/storlets/latest/getting_started.html>`__.

For Engine Developers
---------------------

Getting Started
~~~~~~~~~~~~~~~

The best way to get started is following this guide:
`"Installing a Development Environment" <https://docs.openstack.org/storlets/latest/engine_dev_installation.html>`__.

Tests
~~~~~

There are two types of tests included in the Storlets repo.

 #. Unit tests
 #. Functional tests

Unit tests, are, well, unit tests... The functional tests are black box tests validating
end-to-end scenarios using various storlets, including faulty ones. For more information
please refer to the:
`"Development and Testing Guide" <https://docs.openstack.org/storlets/latest/engine_dev_tests.html>`__.

Repository Structure
~~~~~~~~~~~~~~~~~~~~

- doc/source/: Documentation

- etc/: Sample config files

- storlets/: Python codes

  - agent/: Python code for Docker side agents

    - common/: An agent for storlets process management
    - daemon/: An agent for execution of python applications
    - daemon_factory/: Pyth

  - gateway/: Run time loadable code for managing storlets execution
  - sbus/: A Java implementation of the SBUS communication protocol
  - swift_middleware/: Swift middleware dealing with storlet invocation requests

- StorletSamples/: Storlets examples, used for functional testing

- src/: C and Java codes

  - c/: All codes

    - sbus/: A core implementation of the SBUS protocol, which is used for passing fsd between the middleware and container

  - java/: Java codes

    - SBus:/ A Java implementation of the SBUS communication protocol
    - SCommon/: A Java library required for storlets development
    - SDaemon/: A generic Java daemon for loading storlets at runtime

- tests/: Unit and functional tests

- tools/: Various cluster config dependent tools for automatic and manual testing

For Storlets Developers
-----------------------

Currently, storlets can be developed in Java only.
To get started, follow:
`"S2AIO - Swift Storlets All In One" <https://docs.openstack.org/storlets/latest/s2aio.html>`__.

The write and deploy a storlet, follow:
`"Writing and deploying storlets" <https://docs.openstack.org/storlets/latest/writing_and_deploying_storlets.html>`__.
