#!/bin/bash

set -m

touch /root/.ethereum/passphrase.txt

geth $@ &

sleep 3

n=`ls -1 /root/.ethereum/$NETWORK/keystore | wc -l`

if [ "$n" -eq "0" ]; then
    ./wallet.exp
    echo "0x$(ls /root/.ethereum/$NETWORK/keystore | awk '{split($0,a,"--"); print a[3]}')" > /root/.ethereum/account-$NETWORK.txt
fi

fg %1
