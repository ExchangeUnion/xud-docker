#!/bin/bash

set -e

getaddr() {
    addr=`cat /root/.ethereum/account-$NETWORK.txt | head -1`
}

getaddr

while [ -z "$addr" ]; do
    sleep 3
    echo "Waiting for the parity $NETWORK account"
    getaddr
done

addr="${addr: -40}"
# Address must be EIP55 checksummed
addr=`/opt/venv/bin/python3 /a.py $addr`

/opt/venv/bin/python3 -m raiden --address $addr $@
