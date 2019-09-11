#!/bin/bash

set -euo pipefail

if [[ ! -e ~/.raiden ]]; then
    mkdir ~/.raiden
fi

if [[ ! -e ~/.raiden/config.toml ]]; then
    touch ~/.raiden/config.toml
fi

source /opt/venv/bin/activate

while [ ! -f /root/.ethereum/account-$NETWORK.txt ]; do
    sleep 3
    echo "Waiting for the GETH $NETWORK account"
done

addr=`cat /root/.ethereum/account-$NETWORK.txt | head -1`
addr="${addr: -40}"

# Address must be EIP55 checksummed
addr=`python /checksum.py $addr`

python /configWriter.py $NETWORK

IP="$(hostname -i)"

python -m raiden --address $addr --api-address $IP:5001 $@
