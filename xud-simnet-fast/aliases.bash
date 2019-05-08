#!/bin/bash

alias btcctl="docker-compose exec btcd btcctl --simnet --rpcuser=xu --rpcpass=xu"
alias ltcctl="docker-compose exec ltcd ltcctl --simnet --rpcuser=xu --rpcpass=xu"
alias lncli1="docker-compose exec lndbtc lncli -n simnet -c bitcoin"
alias lncli2="docker-compose exec lndltc lncli -n simnet -c litecoin"
alias xucli="docker-compose exec xud xucli"
