#!/bin/bash

set -e

addr=`ls /root/.ethereum/$NETWORK/keystore/ | head -1`

while [ -z "$addr" ]; do
    sleep 3
    echo "Waiting for the geth account"
    addr=`ls /root/.ethereum/$NETWORK/keystore/ | head -1`
done


addr="${addr: -40}"
# Address must be EIP55 checksummed
addr=`/opt/venv/bin/python3 /a.py $addr`

/opt/venv/bin/python3 -m raiden --address $addr $@