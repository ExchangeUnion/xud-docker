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
parity="docker-compose exec -T parity parity --chain ropsten"
xud="docker-compose exec -T xud xucli"

status_text() {
    if [ -z "$1" ] || [ -z "$2" ]; then
        echo "Waiting for sync"
    else
        if [ $1 -eq $2 ]; then
            echo "Ready"
        else
            p=`echo "$1/$2*100" | bc -l`
            pp=`echo "$p*100/1" | bc`
            ppp=`echo "$pp/100" | bc -l`
            printf "Syncing %.2f%% (%d/%d)\n" $ppp $1 $2
        fi
    fi
}

status_text2() {
    if [ -z "$1" ] || [ -z "$2" ]; then
        echo "Waiting for sync"
    else
        if [ $1 -eq $2 ]; then
            echo "Ready"
        else
            echo "Waiting for sync"
        fi
    fi
}

check_container() {
    if ! docker-compose ps | grep Up | grep $1 >/dev/null 2>&1; then
        echo "Container down"
        return 1
    fi
    return 0
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
    status_text2 $x $y
}

nocolor() {
    sed -r "s/\x1b\[([0-9]{1,2}(;[0-9]{1,2})?)?m//g"
}

geth_status() {
    a=(`$geth --exec 'eth.syncing' attach 2>/dev/null | nocolor | grep -A 1 currentBlock | grep -Po '\d+'`)
    status_text ${a[@]}
}

parity_status() {
    a=(`curl -s -X POST -H "Content-Type: application/json"  \
--data '{"jsonrpc":"2.0","method":"eth_syncing","params":[],"id":1}' http://127.0.0.1:8545 | \
sed 's/^.*"currentBlock":"0x\([0-9a-f]\+\)","highestBlock":"0x\([0-9a-f]\+\)".*$/\1\n\2/' | \
tr 'a-f' 'A-F' | \
xargs -n 1 -I {} sh -c "echo 'obase=10;ibase=16;{}' | bc"`)
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
    echo -e "btc\t$(check_container bitcoind && bitcoind_status btc)"
    echo -e "lndbtc\t$(check_container lndbtc && lnd_status btc)"
    echo -e "ltc\t$(check_container litecoind && bitcoind_status ltc)"
    echo -e "lndltc\t$(check_container lndltc && lnd_status ltc)"
    #echo -e "eth\t$(check_container geth && geth_status)"
    echo -e "parity\t$(check_container parity && parity_status)"
    echo -e "raiden\t$(check_container raiden && raiden_status)"
    echo -e "xud\t$(check_container xud && xud_status)"
}

table() {
    while read line; do
        echo "$line"
    done
}

all_status | table 2>/dev/null
