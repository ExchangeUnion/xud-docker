#!/bin/sh

CHAIN="bitcoin"
RPCHOST="btcd:18556"
if [ "$BACKEND" == "ltcd" ]; then
    CHAIN="litecoin"
    RPCHOST="ltcd:18556"
fi

sleep 20

# macaroons is force enabled when listening on public interfaces (--no-macaroons)
# specify 0.0.0.0:10009 instead of :10009 because `lncli -n simnet getinfo` will not work with ':10009'
lnd --nobootstrap --noseedbackup --debuglevel=debug --maxpendingchannels=10 \
--rpclisten=0.0.0.0:10009 --listen=0.0.0.0:9735 --restlisten=0.0.0.0:8080 --alias=$ALIAS \
--$CHAIN.active --$CHAIN.simnet --$BACKEND.rpchost=$RPCHOST --$BACKEND.rpcuser=xu --$BACKEND.rpcpass=xu $@