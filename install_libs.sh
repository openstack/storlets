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

# Install container side scripts
SRC=bin
DST=/usr/local/libexec/storlets
mkdir -p -m 755 $DST
cp "$SRC/init_container.sh" $DST
