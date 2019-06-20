#!/bin/bash

set -eumo pipefail

ETHEREUM_HOME=~/.local/share/io.parity.ethereum

touch $ETHEREUM_HOME/passphrase.txt

parity $@ &

sleep 3

if [ "$NETWORK" = "testnet" ]; then 
    chain="ropsten"
else
    echo "Unexpected NETWORK: $NETWORK"
    exit 1
fi

accounts=`parity --chain $chain account list`

if [ -z "$accounts" ]; then
    ./wallet.exp "$chain" ""
    addr=`parity --chain $chain account list`
    echo "$addr" > /root/.local/share/io.parity.ethereum/account-$NETWORK.txt
fi

fg %1
