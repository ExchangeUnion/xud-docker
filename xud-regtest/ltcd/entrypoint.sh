#!/bin/bash

# turn on bash's job control
set -m

if [ -e /root/.ltcwallet ]; then
    mkdir -p /root/.ltcwallet/simnet
    mv /wallet.db /root/.ltcwallet/simnet/
    touch /root/.ltcwallet/ltcwallet.conf
fi


if [ -e /root/.ltcd ]; then
    mkdir /root/.ltcd
    touch /root/.ltcd/ltcd.conf
fi

ltcd --simnet --txindex --rpcuser=xu --rpcpass=xu --rpclisten=:18556 --nolisten --miningaddr="$(cat /miningaddr)" $@ &

sleep 1

until ltcctl --simnet --rpcuser=xu --rpcpass=xu getinfo
do
  echo "Sleep 1 second then try again"
  sleep 1
done

ltcwallet --simnet --username=xu --password=xu --rpclisten=:18554

fg %1
