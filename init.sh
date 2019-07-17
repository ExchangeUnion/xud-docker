export XUD_NETWORK=`basename $(pwd)`

case $XUD_NETWORK in
    testnet)
        alias bitcoin-cli="docker-compose exec bitcoind bitcoin-cli -testnet -rpcuser=xu -rpcpassword=xu"
        alias litecoin-cli="docker-compose exec litecoind litecoin-cli -testnet -rpcuser=xu -rpcpassword=xu"
        alias lndbtc-lncli="docker-compose exec lndbtc lncli -n testnet -c bitcoin"
        alias lndltc-lncli="docker-compose exec lndltc lncli -n testnet -c litecoin"
        #alias geth="docker-compose exec geth geth --testnet"
        alias parity="docker-compose exec parity parity --chain ropsten"
        alias xucli="docker-compose exec xud xucli"
        ;;
    simnet)
        #alias btcctl="docker-compose exec btcd btcctl --simnet --rpcuser=xu --rpcpass=xu"
        alias ltcctl="docker-compose exec ltcd ltcctl --simnet --rpcuser=xu --rpcpass=xu"
        alias lndbtc-lncli="docker-compose exec lndbtc lncli -n simnet -c bitcoin"
        alias lndltc-lncli="docker-compose exec lndltc lncli -n simnet -c litecoin"
        alias parity="docker-compose exec parity parity --chain ropsten"
        alias xucli="docker-compose exec xud xucli"
        ;;
esac

alias logs="docker-compose logs"
alias start="docker-compose start"
alias stop="docker-compose stop"
alias restart="docker-compose restart"
alias up="docker-compose up"
alias down="docker-compose down"
    
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
alias orderbook="xucli orderbook"

export PS1="$XUD_NETWORK > "

export XUD_DOCKER_HOME=~/.xud-docker

alias status="$XUD_DOCKER_HOME/status.sh"

report() {
    echo "Please click on https://github.com/ExchangeUnion/xud/issues/new?assignees=kilrau&labels=bug&template=bug-report.md&title=Short%2C+concise+description+of+the+bug, describe your issue, drag and drop the file \"xud-docker.log\" which is usually located in ~/.xud-docker into your browser window and submit your issue."
}

alias report="report"

cat ../banner.txt