===============
Getting Started
===============

This is a TL-DR guide to get you started with Storlet experimentation
as fast as possible.


-------------------
System Requirements
-------------------

Ubuntu Server 14.04 with total disk of 10Gb.
A disposal VM is always a good idea.


-------------------
Installation Guide
-------------------

Make sure to have a user that can sudo without a password.
With that user just do:

::

    sudo apt-get update
    sudo apt-get install python-tox python-nose git
    git clone https://github.com/openstack/storlets.git
    cd storlets
    ./s2aio.sh dev

---------------------------------------
Writing Deploying and Running a Storlet
---------------------------------------

Browse through the StorletSamples directory so see storlet code examples,
and through the tests/functional to see samples of deploying and invoking
a storlet.
