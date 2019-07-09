#!/bin/bash

stop_litecoind() {
    cli="litecoin-cli -$NETWORK -rpcuser=xu -rpcpassword=xu"
    while ! $cli stop; do
        sleep 10
    done
}

trap stop_litecoind SIGINT SIGTERM

litecoind $@
