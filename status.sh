#!/bin/bash

set -euo pipefail

# using -T to solve docker-compose error:
# the input device is not a TTY
# ref. https://github.com/docker/compose/issues/5696

bitcoind="docker-compose exec -T bitcoind bitcoin-cli -rpcuser=xu -rpcpassword=xu"
litecoind="docker-compose exec -T litecoind litecoin-cli -rpcuser=xu -rpcpassword=xu"

lndbtc="docker-compose exec -T lndbtc lncli -n $XUD_NETWORK -c bitcoin"
lndltc="docker-compose exec -T lndltc lncli -n $XUD_NETWORK -c litecoin"
geth="docker-compose exec -T geth geth"
xud="docker-compose exec -T xud xucli"

btcd="docker-compose exec btcd btcctl --$XUD_NETWORK --rpcuser=xu --rpcpass=xu"
ltcd="docker-compose exec ltcd ltcctl --$XUD_NETWORK --rpcuser=xu --rpcpass=xu"

if [ "$XUD_NETWORK" != "mainnet" ]; then
    bitcoind+=" -$XUD_NETWORK"
    litecoind+=" -$XUD_NETWORK"
    geth+=" --$XUD_NETWORK"
fi

status_text() {
    if [[ $# -lt 2 ]]; then
        echo "Waiting for sync"
        return
    fi
    if [[ -z $1 || -z $2 ]]; then
        echo "Waiting for sync"
    elif [[ $1 -gt $2 ]]; then
        echo "Syncing 99.99%"
    else
        if [[ $1 == $2 ]]; then
            echo "Ready"
        else
            local x=`echo "$1/$2*100" | bc -l`
            local y=`echo "$x*100/1" | bc`
            local z=`echo "$y/100" | bc -l`
            LC_NUMERIC="en_US.UTF-8" printf "Syncing %.2f%% (%d/%d)\n" $z $1 $2
        fi
    fi
}

status_text2() {
    if [[ $1 == $2 ]]; then
        echo "Ready"
    else
        echo "Waiting for sync"
    fi
}

check_container() {
    if ! docker-compose ps | grep Up | grep $1 >/dev/null 2>&1; then
        echo "Container down"
        return 1
    fi
    return 0
}

btc_status() {
    set +e
    set +o pipefail

    if [[ $XUD_NETWORK == "simnet" ]]; then
        if [[ $1 == "btc" ]]; then
            local pre="$btcd"
        else
            local pre="$ltcd"
        fi
    else
        if [[ $1 == "btc" ]]; then
            local pre="$bitcoind"
        else
            local pre="$litecoind"
        fi
    fi
    local info=`$pre getblockchaininfo 2>&1`
    local args=`echo "$info" | grep -A 1 blocks | sed -nE 's/[^0-9]*([0-9]+).*/\1/p' | paste -sd ' ' -`
    if [[ -z $args ]]; then
        echo "$info" | tail -1
    else
        status_text $args
    fi
}

lnd_status() {
    if [[ $XUD_NETWORK == "simnet" ]]; then
        if [[ $1 == "btc" ]]; then
            local pre1="$btcd"
            local pre2="$lndbtc"
        else
            local pre1="$ltcd"
            local pre2="$lndltc"
        fi
    else
        if [[ $1 == "btc" ]]; then
            local pre1="$bitcoind"
            local pre2="$lndbtc"
        else
            local pre1="$litecoind"
            local pre2="$lndltc"
        fi
    fi
    local y=`$pre1 getblockchaininfo 2>/dev/null | grep -A 1 blocks | sed -nE 's/[^0-9]*([0-9]+).*/\1/p' | tail -1`
    local x=`$pre2 getinfo 2>/dev/null | grep block_height | sed -nE 's/[^0-9]*([0-9]+).*/\1/p'`
    if [[ -z $x || -z $y ]]; then
        if $pre2 getinfo 2>/dev/null | grep '"synced_to_chain": true' >/dev/null; then
            echo "Ready"
        else
            echo "Waiting for sync"
        fi
        return
    fi
    status_text2 $x $y
}

nocolor() {
    sed -r "s/\x1b\[([0-9]{1,2}(;[0-9]{1,2})?)?m//g"
}

geth_status() {
    local status=`$geth --exec 'eth.syncing' attach 2>/dev/null`

    if [[ $status != "false" ]]; then
        status=`echo "$status" | nocolor | grep -A 1 currentBlock | sed -nE 's/[^0-9]*([0-9]+).*/\1/p' | paste -sd ' ' -`
	    status_text $status
    else
        # If 'eth.syncing' is false and 'eth.blockNumber' is 0 the sync has not started yet
        if [[ `$geth --exec 'eth.blockNumber' attach 2>/dev/null` == "0" ]]; then
            status_text
        else
    	    status_text2 $status $status
        fi
    fi
}

raiden_status() {
    local port=`docker-compose ps | grep raiden | sed -nE 's/.*:([0-9]+)-.*/\1/p'`
    local sync=`curl -is http://localhost:$port/api/v1/tokens | grep "200 OK"`
    if [[ -z $sync ]]; then
        echo "Waiting for sync"
    else
        echo "Ready"
    fi
}

xud_status() {
    local info=`$xud getinfo 2>/dev/null`
    local lndbtc_ok=`echo "$info" | grep -A2 BTC | grep error | grep '""'`
    local lndltc_ok=`echo "$info" | grep -A2 LTC | grep error | grep '""'`
    local raiden_ok=`echo "$info" | grep -A1 raiden | grep error | grep '""'`

    if [[ ! -z $lndbtc_ok && ! -z $lndltc_ok  && ! -z $raiden_ok ]]; then
        echo "Ready"
    else
        echo "Waiting for sync"
    fi
}

all_status() {
    echo -e "SERVICE\tSTATUS"

    if [[ $XUD_NETWORK == "simnet" ]]; then
        local btc_service="btcd"
        local ltc_service="ltcd"
    else
        local btc_service="bitcoind"
        local ltc_service="litecoind"
    fi

    if [[ $XUD_NETWORK != "simnet" ]]; then
        echo -e "btc\t$(check_container $btc_service && btc_status btc)"
    fi
    echo -e "lndbtc\t$(check_container lndbtc && lnd_status btc)"
    echo -e "ltc\t$(check_container $ltc_service && btc_status ltc)"
    echo -e "lndltc\t$(check_container lndltc && lnd_status ltc)"
    if [[ $XUD_NETWORK != "simnet" ]]; then
        echo -e "geth\t$(check_container geth && geth_status)"
    fi
    echo -e "raiden\t$(check_container raiden && raiden_status)"
    echo -e "xud\t$(check_container xud && xud_status)"
}

table() {
    while read line; do
        echo "$line"
    done
}

all_status | table 2>/dev/null
