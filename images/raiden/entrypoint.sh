#!/bin/bash

set -euo pipefail

whoami

if [[ ! -e ~/.raiden ]]; then
    mkdir ~/.raiden
fi

if [[ ! -e ~/.raiden/config.toml ]]; then
    touch ~/.raiden/config.toml
fi

ls ~/.raiden

getaddr() {
    addr=`cat /root/.ethereum/account-$NETWORK.txt | head -1`
}

source /opt/venv/bin/activate

if [ "$NETWORK" = "testnet" ]; then
    getaddr

    while [ -z "$addr" ]; do
        sleep 3
        echo "Waiting for the parity $NETWORK account"
        getaddr
    done

    addr="${addr: -40}"

    # Address must be EIP55 checksummed
    addr=`/opt/venv/bin/python3 /checksum.py $addr`
else
    cd /root/.raiden
    if ! [ -e "addr.txt" ]; then
        addr=`python /onboarder.py | tail -1 | awk '{print $2}'`
        echo "$addr" > addr.txt
        echo "123123123" > password.txt
    else
        addr=`cat addr.txt`
    fi
fi

python /configWriter.py $NETWORK

python -m raiden --address $addr $@
