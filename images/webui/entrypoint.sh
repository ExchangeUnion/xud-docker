#!/bin/sh

case $NETWORK in
    simnet)
        RPCPORT=28886
        ;;
    testnet)
        RPCPORT=18886
        ;;
    mainnet)
        RPCPORT=8886
        ;;
    *)
        echo "Invalid NETWORK"
        exit 1
esac

while ! [ -e /root/.xud/tls.cert ]; do
    echo "Waiting for /root/.xud/tls.cert"
    sleep 1
done

exec bin/server --xud.rpchost=xud --xud.rpcport=$RPCPORT --xud.rpccert=/root/.xud/tls.cert \
--pairs.weight btc_usdt:4,eth_btc:3,ltc_btc:2,ltc_usdt:1 $WEBUI_OPTS
