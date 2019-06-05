#!/bin/bash

alias bitcoin-cli="docker-compose exec bitcoind bitcoin-cli -testnet -rpcuser=xu -rpcpassword=xu"
alias litecoin-cli="docker-compose exec litecoind litecoin-cli -testnet -rpcuser=xu -rpcpassword=xu"
alias lndbtc-lncli="docker-compose exec lndbtc lncli -n testnet -c bitcoin"
alias lndltc-lncli="docker-compose exec lndltc lncli -n testnet -c litecoin"
alias geth="docker-compose exec geth geth --testnet"
alias xucli="docker-compose exec xud xucli"
alias xucli-status="docker-compose exec xud status"