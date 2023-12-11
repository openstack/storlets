#!/bin/bash
#
# Install required libraries written in c and java
#
# NOTE: The libraries are currently installed under /usr/lib/storlets
#       so you may need root privilege to execute this script
set -x

# install c library
cd src/c/sbus
make && make install
cd -

# Install java library
ant install
