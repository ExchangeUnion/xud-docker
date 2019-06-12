#!/bin/bash

set -m

touch /root/.ethereum/passphrase.txt

geth $@ &

sleep 3

n=`ls -1 /root/.ethereum/$NETWORK/keystore | wc -l`

if [ "$n" -eq "0" ]; then
    ./wallet.exp
fi

fg %1