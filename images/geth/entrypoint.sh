#!/bin/bash
set -m

GETH_HOME=/root/.ethereum

touch $GETH_HOME/passphrase.txt

./create-account.sh &

OPTS=""

if [[ -e $GETH_HOME/peers.txt ]]; then
    OPTS="$OPTS --bootnodes=$(cat /root/.ethereum/peers.txt | paste -sd ',' -)"
else
    case $NETWORK in
        testnet)
            OPTS="$OPTS --bootnodes=$(cat /ropsten-peers.txt | paste -sd ',' -)"
            ;;
        mainnet)
            OPTS="$OPTS --bootnodes=$(cat /mainnet-peers.txt | paste -sd ',' -)"
            ;;
    esac
fi

exec geth $OPTS --rpcaddr "$(hostname -i)" $@
