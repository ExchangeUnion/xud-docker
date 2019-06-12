#!/bin/bash

set -e

echo "Should success when first install"
tests/xud.exp

echo "*****************************************"
echo "Should append aliases to bashrc"
if grep 'Add xud-docker aliases' ~/.bashrc; then
    echo "Aliases exists"
else
    echo "Missing aliases"
    exit 1
fi

shopt -s expand_aliases
source ~/.bashrc

set -x

echo "*****************************************"
echo "Should print cluster status when run xucli-status"
which xucli-status
xucli-status

echo "*****************************************"
echo "Should print xud info when run xucli getinfo"
which xucli
xucli getinfo
