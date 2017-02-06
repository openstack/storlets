Development and Testing Guide
=============================

This guide explains how to build the various components, and how to deploy them once built.
Note that some of the components being built need to be inserted to a docker image before
they can be tested. Thus, one should have an installed environment as described in
the development environment installation instructions_ or in the getting started guide_

.. _instructions: engine_dev_installation.html
.. _guide: getting_started.html

Building
--------
The storlets repository consists of code written in Python, Java and C.
The C and Java code reside under the 'src/' directory. The C code is built and
installed using Makefiles, and the Java code is built and installed using ant
build.xml files. Refer to the instal_libs.sh script under the repo root directory
for the exact procedure of building and installing the C and Java code.

The python code resides under the storlets directory and is installed using the usual
setup.py script.

In addition there are several storlet examples written in both Python and Java under the
StorletSamples directory. This directory has a build.xml script used to build the samples.
To build the storlets cd to the StorletSamples/java directory and run:

::

    ant build

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

    ./.functests dev

.. note::

  To run the entire set of functional tests, which takes longer run:
  ./.functests jenkins

from the repo root.

.. note::

  Other than testing, those tests are a good reference for writing and deploying storlets.
