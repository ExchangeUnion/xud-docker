#!/bin/sh

if [ -e "/data.tar.gz" ]; then
    echo "Extract blocks data"
    mkdir -p /root/.btcd/data/simnet/blocks_ffldb
    tar -C /root/.btcd/data/simnet/blocks_ffldb -zxvf /data.tar.gz
    rm /data.tar.gz
    touch /root/.btcd/btcd.conf
fi

btcd --simnet --txindex --rpcuser=xu --rpcpass=xu --rpclisten=:18556 --nolisten $@
