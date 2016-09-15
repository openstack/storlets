#!/bin/bash
#
# Install required libraries written in c and java
#
# NOTE: The libraries are currently installed under /usr/lib/storlets
#       so you may need root priviledge to execute this script

# build scripts
cd scripts
# TODO(takashi): also install them
make
cd -

# install c library
cd src/c/sbus
make && make install
cd -

# Install java library
ant install
