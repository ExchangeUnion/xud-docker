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

export XUD_DOCKER_HOME=~/.xud-docker

alias status="$XUD_DOCKER_HOME/status.sh"