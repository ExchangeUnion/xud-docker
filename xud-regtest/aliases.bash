#!/bin/bash

alias btcctl="docker-compose exec btcd btcctl --simnet --rpcuser=xu --rpcpass=xu $@"
alias ltcctl="docker-compose exec ltcd ltcctl --simnet --rpcuser=xu --rpcpass=xu $@"
alias lncli1="docker-compose exec lndbtc1 lncli -n simnet -c bitcoin $@"
alias lncli2="docker-compose exec lndbtc2 lncli -n simnet -c bitcoin $@"
alias lncli3="docker-compose exec lndltc1 lncli -n simnet -c litecoin $@"
alias lncli4="docker-compose exec lndltc2 lncli -n simnet -c litecoin $@"
alias xucli1="docker-compose exec xud1 xucli $@"
alias xucli2="docker-compose exec xud2 xucli $@"
