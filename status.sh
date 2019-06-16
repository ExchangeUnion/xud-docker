#!/bin/bash

set -eo pipefail

# using -T to solve docker-compose error:
# the input device is not a TTY
# ref. https://github.com/docker/compose/issues/5696

bitcoind="docker-compose exec -T bitcoind bitcoin-cli -testnet -rpcuser=xu -rpcpassword=xu"
litecoind="docker-compose exec -T litecoind litecoin-cli -testnet -rpcuser=xu -rpcpassword=xu"
lndbtc="docker-compose exec -T lndbtc lncli -n testnet -c bitcoin"
lndltc="docker-compose exec -T lndltc lncli -n testnet -c litecoin"
geth="docker-compose exec -T geth geth --testnet"
xud="docker-compose exec -T xud xucli"

status_text() {
    if [ -z "$1" ] || [ -z "$2" ]; then
        echo "Waiting for sync"
    else
        if [ $1 -eq $2 ]; then
            echo "Ready"
        else
            printf "Syncing %.2f%% (%d/%d)\n" $(echo "$1/$2*100" | bc -l) $1 $2
        fi
    fi
}

bitcoind_status() {
    set +e
    set +o pipefail

    if [ $1 = "btc" ]; then
        pre="$bitcoind"
    else
        pre="$litecoind"
    fi
    a=(`$pre getblockchaininfo 2>/dev/null | grep -A 1 blocks | grep -Po '\d+'`)
    status_text ${a[@]}
}

lnd_status() {
    if [ $1 = "btc" ]; then
        pre1="$bitcoind"
        pre2="$lndbtc"
    else
        pre1="$litecoind"
        pre2="$lndltc"
    fi
    y=`$pre1 getblockchaininfo 2>/dev/null | grep -A 1 blocks | grep -Po '\d+' | tail -1`
    x=`$pre2 getinfo 2>/dev/null | grep block_height | grep -Po '\d+'`
    status_text $x $y
}

nocolor() {
    sed -r "s/\x1b\[([0-9]{1,2}(;[0-9]{1,2})?)?m//g"
}

geth_status() {
    a=(`$geth --exec 'eth.syncing' attach | nocolor | grep -A 1 currentBlock | grep -Po '\d+'`)
    status_text ${a[@]}
}

raiden_status() {
    sync=`docker-compose logs --tail=10 raiden 2>/dev/null | grep 'Waiting for the ethereum node to synchronize'`
    if [ -z "$sync" ]; then
        echo "Ready"
    else
        echo "Waiting for sync"
    fi
}

xud_status() {
    info=`$xud getinfo 2>/dev/null`
    lndbtc_error=`echo $info | grep -A 2 BTC | grep error`
    lndltc_error=`echo $info | grep -A 2 LTC | grep error`
    raiden_error=`echo $info | grep -A 1 raiden | grep error`

    if ! [ -z "$lndbtc_error" ] || ! [ -z "$lndltc_error" ] || ! [ -z "$raiden_error" ]; then
        echo "Waiting for sync"
    else
        echo "Ready"
    fi
}

all_status() {
    echo -e "SERVICE\tSTATUS"
    echo -e "btc\t$(bitcoind_status btc)"
    echo -e "ltc\t$(bitcoind_status ltc)"
    echo -e "lndbtc\t$(lnd_status btc)"
    echo -e "lndltc\t$(lnd_status ltc)"
    echo -e "eth\t$(geth_status)"
    echo -e "raiden\t$(raiden_status)"
    echo -e "xud\t$(xud_status)"
}

table() {
    while read line; do
        echo "$line"
    done
}

all_status | table 2>/dev/null
