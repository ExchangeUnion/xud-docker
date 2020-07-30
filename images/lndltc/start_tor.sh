#!/usr/bin/env bash

case $CHAIN in
    bitcoin)
        PORT=9735
        ;;
    litecoin)
        PORT=10735
        ;;
esac

if [[ $NETWORK == "testnet" ]]; then
    PORT=$((PORT + 10000))
fi

sed -i "s/<port>/$PORT/g" /etc/tor/torrc

tor -f /etc/tor/torrc
