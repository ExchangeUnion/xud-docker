#!/bin/bash

set -euo pipefail

LND_DIR="$HOME/.lnd"
TOR_HOSTNAME="$HOME/.tor/service/hostname"

function wait_file() {
    local FILE="$1"
    while [[ ! -e $FILE ]]; do
        sleep 1
    done
}

function wait_9050() {
    while ! nc -z tor 9050; do
        sleep 1
    done
}

###############################################################################

mkdir -p $LND_DIR
if [[ $CHAIN == "bitcoin" ]]; then
    echo "Using configuration for bitcoin"
    cp /tmp/lnd-btc.conf $LND_DIR/lnd.conf
else
    echo "Using configuration for litecoin"
    cp /tmp/lnd-ltc.conf $LND_DIR/lnd.conf
fi

echo "Waiting for LND ($CHAIN) onion address..."
wait_file "$TOR_HOSTNAME"
LND_ONION_ADDRESS=$(cat "$TOR_HOSTNAME")
echo "Onion address for LND ($CHAIN) is $LND_ONION_ADDRESS"

echo "Waiting for tor 9050 socks port to be open..."
wait_9050

lnd --lnddir=$LND_DIR --externalip="$LND_ONION_ADDRESS" --$CHAIN.$NETWORK $@
