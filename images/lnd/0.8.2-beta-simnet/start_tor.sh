#!/usr/bin/env bash

case $CHAIN in
    bitcoin)
        PORT=29735
        ;;
    litecoin)
        PORT=30735
        ;;
esac

sed -i "s/<port>/$PORT/g" /etc/tor/torrc

tor -f /etc/tor/torrc
