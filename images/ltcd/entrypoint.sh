#!/bin/sh

if [ -e "/data.tar.gz" ]; then
    echo "Extract blocks data"
    mkdir -p /root/.ltcd/data/$NETWORK/blocks_ffldb
    tar -C /root/.ltcd/data/$NETWORK/blocks_ffldb -zxvf /data.tar.gz
    rm /data.tar.gz
    touch /root/.ltcd/ltcd.conf
fi

ltcd $@
