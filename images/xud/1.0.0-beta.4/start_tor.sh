#!/usr/bin/env bash

PORT=8885
if [[ $NETWORK == "testnet" ]]; then
    PORT=$((PORT + 10000))
fi

sed -i "s/<port>/$PORT/g" /etc/tor/torrc

tor -f /etc/tor/torrc
