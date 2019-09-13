#!/bin/bash
set -m

touch /root/.ethereum/passphrase.txt

./create-account.sh &

case $NETWORK in
    testnet)
        OPTS="--bootnodes='$(cat /root/.ethereum/ropsten-peers.txt | paste -sd ',' -)'"
        ;;
    mainnet)
        OPTS="--bootnodes='$(cat /root/.ethereum/mainnet-peers.txt | paste -sd ',' -)'"
        ;;
    *)
        OPTS=""
        ;;
esac

exec geth $OPTS --rpcaddr "$(hostname -i)" $@
