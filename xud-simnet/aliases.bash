#!/bin/bash

alias btcctl="docker-compose exec btcd btcctl --simnet --rpcuser=xu --rpcpass=xu"
alias ltcctl="docker-compose exec ltcd ltcctl --simnet --rpcuser=xu --rpcpass=xu"
alias lndbtc-lncli="docker-compose exec lndbtc lncli -n simnet -c bitcoin"
alias lndltc-lncli="docker-compose exec lndltc lncli -n simnet -c litecoin"
alias xucli="docker-compose exec xud xucli"
alias logs="docker-compose logs"
