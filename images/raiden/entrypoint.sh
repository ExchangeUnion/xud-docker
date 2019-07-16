#!/bin/bash

set -euo pipefail

if [[ ! -e ~/.raiden ]]; then
    mkdir ~/.raiden
fi

if [[ ! -e ~/.raiden/config.toml ]]; then
    touch ~/.raiden/config.toml
fi

getaddr() {
    addr=`cat /root/.ethereum/account-$NETWORK.txt | head -1`
}

source /opt/venv/bin/activate

if [[ $NETWORK == "testnet" ]]; then
    getaddr

    while [ -z "$addr" ]; do
        sleep 3
        echo "Waiting for the parity $NETWORK account"
        getaddr
    done

    addr="${addr: -40}"

    # Address must be EIP55 checksummed
    addr=`python /checksum.py $addr`
fi

python /configWriter.py $NETWORK

python -m raiden --address $addr $@
