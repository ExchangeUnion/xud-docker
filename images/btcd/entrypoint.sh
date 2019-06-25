#!/bin/sh

if [ -e "/data.tar.gz" ]; then
    echo "Extract blocks data"
    mkdir -p /root/.btcd/data/$NETWORK/blocks_ffldb
    tar -C /root/.btcd/data/$NETWORK/blocks_ffldb -zxvf /data.tar.gz
    rm /data.tar.gz
    touch /root/.btcd/btcd.conf
fi

btcd $@
