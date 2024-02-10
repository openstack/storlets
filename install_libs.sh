#!/bin/bash
#
# Install required libraries written in c and java
#
# NOTE: The libraries are currently installed under /usr/lib/storlets
#       so you may need root privilege to execute this script
set -x

STORLETS_JDK_VERSION=${STORLETS_JDK_VERSION:-11}

# install c library
cd src/c/sbus
make && make install
cd -

# Install java library
STORLETS_JDK_VERSION=${STORLETS_JDK_VERSION} ant install
