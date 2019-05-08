#!/bin/bash

set -m

if [ -e "/data.tar.gz" ]; then
    tar -C /root/.lnd -zxvf /data.tar.gz
fi

BACKEND="btcd"
CHAIN="bitcoin"
RPCHOST="btcd:18556"
CERT="/btcd.cert"
PEER="030c2ffd29a92e2dd2fb6fb046b0d9157e0eda8b11caa0e439d0dd6a46a444381@35.229.81.83:10012"

# macaroons is force enabled when listening on public interfaces (--no-macaroons)
# specify 0.0.0.0:10009 instead of :10009 because `lncli -n simnet getinfo` will not work with ':10009'
lnd --nobootstrap --noseedbackup --debuglevel=debug --maxpendingchannels=10 \
--rpclisten=0.0.0.0:10009 --listen=0.0.0.0:9735 --restlisten=0.0.0.0:8080 --alias=$ALIAS \
--$CHAIN.active --$CHAIN.simnet --$BACKEND.rpchost=$RPCHOST --$BACKEND.rpcuser=xu --$BACKEND.rpcpass=xu \
--$BACKEND.rpccert=$CERT &

sleep 20

until lncli -n simnet -c $CHAIN getinfo
do
    echo "Will try getinfo in 1 second"
    sleep 10
done

lncli -n simnet -c $CHAIN connect $PEER

fg %1
