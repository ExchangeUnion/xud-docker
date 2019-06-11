export PS1='> '

alias bitcoin-cli="docker-compose exec bitcoind bitcoin-cli -testnet -rpcuser=xu -rpcpassword=xu"
alias litecoin-cli="docker-compose exec litecoind litecoin-cli -testnet -rpcuser=xu -rpcpassword=xu"
alias lndbtc-lncli="docker-compose exec lndbtc lncli -n testnet -c bitcoin"
alias lndltc-lncli="docker-compose exec lndltc lncli -n testnet -c litecoin"
alias geth="docker-compose exec geth geth --testnet"
alias xucli="docker-compose exec xud xucli"

alias help="xucli help"
alias addcurrency="xucli addcurrency"
alias addpair="xucli addpair"
alias ban="xucli ban"
alias channelbalance="xucli channelbalance"
alias connect="xucli connect"
alias executeswap="xucli executeswap"
alias getinfo="xucli getinfo"
alias getnodeinfo="xucli getnodeinfo"
alias listorders="xucli listorders"
alias listpairs="xucli listpairs"
alias listpeers="xucli listpeers"
alias removecurrency="xucli removecurrency"
alias removeorder="xucli removeorder"
alias removepair="xucli removepair"
alias shutdown="xucli shutdown"
alias unban="xucli unban"
alias buy="xucli buy"
alias sell="xucli sell"

home=`pwd`

nocolor() {
    sed -r "s/\x1b\[([0-9]{1,2}(;[0-9]{1,2})?)?m//g"
}

raiden_status() {
    echo "Waiting for sync"
}

xud_status() {
    info=`xucli getinfo`
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
    set -euo pipefail

    if ! [ -e $home/tmp/status ]; then
        mkdir -p $home/tmp/status
    fi

    tmp=$home/tmp/status

    bitcoin-cli getblockchaininfo | grep -A 1 blocks | grep -Po '\d+' > $tmp/bitcoind
    litecoin-cli getblockchaininfo | grep -A 1 blocks | grep -Po '\d+' > $tmp/litecoind
    lndbtc-lncli getinfo | grep block_height | grep -Po '\d+' > $tmp/lndbtc
    lndltc-lncli getinfo | grep block_height | grep -Po '\d+' > $tmp/lndltc
    geth --exec 'eth.syncing' attach | nocolor | grep -A 1 currentBlock | grep -Po '\d+' > $tmp/geth
    raiden_status > $tmp/raiden
    xud_status > $tmp/xud

    if [ `cat $tmp/bitcoind | wc -l` -eq 2 ]; then
        a=`cat $tmp/bitcoind | sed '1q;d'`
        b=`cat $tmp/bitcoind | sed '2q;d'`
    else
        a=0
        b=0
    fi

    if [ $b -eq 0 ]; then
        btc="Preparing for sync"
    else
        btc=`printf "Syncing %.2f%% (%d/%d)" $(echo "$a/$b*100" | bc -l) $a $b`
    fi

    if [ `cat $tmp/lndbtc | wc -l` -eq 1 ]; then
        a=`cat $tmp/lndbtc`
    else
        a=0
    fi

    if [ $b -eq 0 ]; then
        lndbtc="Waiting for sync"
    else
        lndbtc=`printf "Syncing %.2f%% (%d/%d)" $(echo "$a/$b*100" | bc -l) $a $b`
    fi

    if [ `cat $tmp/litecoind | wc -l` -eq 2 ]; then
        a=`cat $tmp/litecoind | sed '1q;d'`
        b=`cat $tmp/litecoind | sed '2q;d'`
    else
        a=0
        b=0
    fi

    if [ $b -eq 0 ]; then
        ltc="Preparing for sync"
    else
        ltc=`printf "Syncing %.2f%% (%d/%d)" $(echo "$a/$b*100" | bc -l) $a $b`
    fi

    if [ `cat $tmp/lndltc | wc -l` -eq 1 ]; then
        a=`cat $tmp/lndltc`
    else
        a=0
    fi

    if [ $b -eq 0 ]; then
        lndltc="Waiting for sync"
    else
        lndltc=`printf "Syncing %.2f%% (%d/%d)" $(echo "$a/$b*100" | bc -l) $a $b`
    fi

    if [ `cat $tmp/geth | wc -l` -eq 2 ]; then
        a=`cat $tmp/geth | sed '1q;d'`
        b=`cat $tmp/geth | sed '2q;d'`
    else
        a=0
        b=0
    fi

    if [ $b -eq 0 ]; then
        eth="Preparing for sync"
    else
        eth=`printf "Syncing %.2f%% (%d/%d)" $(echo "$a/$b*100" | bc -l) $a $b`
    fi

    raiden=`cat $tmp/raiden`
    xud=`cat $tmp/xud`

    echo -e "SERVICE\tSTATUS"
    echo -e "btc\t$btc"
    echo -e "ltc\t$ltc"
    echo -e "lndbtc\t$lndbtc"
    echo -e "lndltc\t$lndltc"
    echo -e "eth\t$eth"
    echo -e "raiden\t$raiden"
    echo -e "xud\t$xud"

}

table() {
    cat
}

alias status="all_status | table"