#!/bin/bash

stop_litecoind() {
    cli="litecoin-cli -$NETWORK -rpcuser=xu -rpcpassword=xu"
    while ! $cli stop; do
        sleep 10
    done
}

trap stop_litecoind SIGINT SIGTERM

IP="$(hostname -i)"

litecoind -rpcbind=$IP -rpcallowip=::/0 -zmqpubrawblock=tcp://$IP:29332 -zmqpubrawtx=tcp://$IP:29333 $@
