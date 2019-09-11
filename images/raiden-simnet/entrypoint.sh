#!/bin/bash

set -euo pipefail
shopt -s expand_aliases

if [[ ! -e ~/.raiden ]]; then
    mkdir ~/.raiden
fi
cd /root/.raiden

if [[ ! -e "addr.txt" ]]; then
    addr=`python /opt/onboarder.py | tail -1 | awk '{print $2}'`
    echo "$addr" > addr.txt
    echo "123123123" > password.txt
else
    addr=`cat addr.txt`
fi

IP="$(hostname -i)"

python -m raiden --address $addr --api-address $IP:5001 $@
