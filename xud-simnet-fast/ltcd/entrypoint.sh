#!/bin/sh

if [ -e "/data.tar.gz" ]; then
    echo "Extract blocks data"
    mkdir -p /root/.ltcd/data/simnet/blocks_ffldb
    tar -C /root/.ltcd/data/simnet/blocks_ffldb -zxvf /data.tar.gz
    rm /data.tar.gz
    mv /rpc.cert /rpc.key /root/.ltcd
    touch /root/.ltcd/ltcd.conf
fi

ltcd --simnet --txindex --rpcuser=xu --rpcpass=xu --rpclisten=:18556 --nolisten $@
