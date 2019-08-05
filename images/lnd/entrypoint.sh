#!/bin/bash

set -euo pipefail
set -m

args="$@"

lncli="lncli -n $NETWORK -c $CHAIN"
walletfile="~/.lnd/data/chain/$CHAIN/$NETWORK/wallet.db"
logfile="~/.lnd/logs/$CHAIN/$NETWORK/lnd.log"

check_lnd() {
    n=`ps | grep "lnd " | grep -v grep | wc -l`
    [ $n -eq "1" ] && $lncli getinfo > /dev/null 2>&1
}

get_running_lnd_count() {
    ps | grep "lnd " | grep -v grep | wc -l
}

is_lnd_running() {
    [[ $(get_running_lnd_count) -gt 0 ]]
}

open_channels() {

    while ! check_lnd; do
        if ! is_lnd_running; then
            echo "Lnd is dead!!!"
            return 0;
        fi
        sleep 3
    done

    btc_peers=(
        "03a0bdf210dcecebb2d6f092b47fb7753af8114261888a365dfcb0d4548bbbdd2a@xud1.test.exchangeunion.com:10012"
        "036f9b004f047283b33a640bc4afdd26e2eb82e73938f8ac0796641ad20dc5bdd4@xud2.test.exchangeunion.com:10012"
        "023f4a4fa9166f1beb2616bf0cce2c5a4fc9fcda6d533cb760bb6630487bfafdf9@xud3.test.exchangeunion.com:10012"
    )

    ltc_peers=(
        "0270e8254e07649cdde230c9e09de6ff63c28a6d275c30b0a6863028d9db0e7c6f@xud1.test.exchangeunion.com:10011"
        "027dbb21be00a4cace0ce73761449f4d329cd400c08d556e2df4c65cf530c4e689@xud2.test.exchangeunion.com:10011"
        "03e26345aa5d7024668e1f16adc2ecd85907a930820ad5a32736946cb824067eeb@xud3.test.exchangeunion.com:10011"
    )

    if [ "$NETWORK" = "simnet" ]; then
        if [ -e index.txt ]; then
            index=`cat index.txt`
        else
            let index="$RANDOM % 3"
            echo "$index" > index.txt
        fi
        if [ "$CHAIN" = "bitcoin" ]; then
            connectstr="${btc_peers[$index]}"
            echo "[DEBUG] Open channel with $connectstr"
            $lncli connect $connectstr
        else
            connectstr="${ltc_peers[$index]}"
            echo "[DEBUG] Open channel with $connectstr"
            $lncli connect $connectstr
        fi
    fi
}

unlock_wallet() {
    if [[ ! -e $walletfile ]]; then
        ./wallet.exp
    fi

    ./unlock.exp
    # TODO make sure wallet has been unlocked

    # 2019-07-15 19:00:41.217 [INF] LTND: Waiting for wallet encryption password. Use `lncli create` to create a wallet, 
    # `lncli unlock` to unlock an existing wallet, or `lncli changepassword` to change the password of an existing wallet and unlock it.

    if ! tail -1 $logfile | grep 'Waiting for wallet entryption password'; then
        echo "Wallet unlocked!!!"
        return 0
    else
        echo "Failed to unlock wallet!!!"
        return 1
    fi
}

start_lnd() {
    # macaroons is force enabled when listening on public interfaces (--no-macaroons)
    # specify 0.0.0.0:10009 instead of :10009 because `lncli -n simnet getinfo` will not work with ':10009'
    lnd $args --rpclisten=0.0.0.0:10009 --listen=0.0.0.0:9735 --restlisten=0.0.0.0:8080 >>lnd.log 2>&1 &

    unlock_wallet

    open_channels
}



stop_lnd() {
    n=`get_running_lnd_count`
    while [[ $n -gt 0 ]]; do
        ps | grep "lnd " | grep -v grep | awk '{print $1}' | xargs kill -9
        sleep 10
        n=`get_running_lnd_count`
    done
}

restart_lnd() {
    stop_lnd
    start_lnd
}

run() {
    start_lnd &
    sleep 30
    while true; do
        if ! check_lnd; then
            restart_lnd
        fi
        sleep 10
    done
}

run
