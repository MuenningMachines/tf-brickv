#!/bin/sh -e

export PATH=/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin

cd $1
shift
make $@
