#!/bin/bash

# turn on bash's job control
set -m

if [ -e /root/.btcwallet ]; then
    mkdir -p /root/.btcwallet/simnet
    mv /wallet.db /root/.btcwallet/simnet/
    touch /root/.btcwallet/btcwallet.conf
fi


if [ -e /root/.btcd ]; then
    mkdir /root/.btcd
    touch /root/.btcd/btcd.conf
fi

btcd --simnet --txindex --rpcuser=xu --rpcpass=xu --rpclisten=:18556 --nolisten --miningaddr="$(cat /miningaddr)" $@ &

sleep 1

until btcctl --simnet --rpcuser=xu --rpcpass=xu getinfo
do
  echo "Sleep 1 second then try again"
  sleep 1
done

btcwallet --simnet --username=xu --password=xu --rpclisten=:18554

fg %1
