#!/bin/bash

set -euo pipefail

ETHEREUM_DIR=/root/.ethereum
PEERS=$ETHEREUM_DIR/peers.txt
ROPSTEN_PEERS=/ropsten-peers.txt
MAINNET_PEERS=/mainnet-peers.txt

OPTS=(
  "--syncmode fast"
  "--rpc"
  "--rpcaddr 0.0.0.0"
  "--rpcapi eth,net,web3,txpool,personal,admin"
  "--rpcvhosts=*"
  "--cache=256"
  "--nousb"
)

if [[ $CUSTOM_ANCIENT_CHAINDATA == "true" ]]; then
    OPTS+=("--datadir.ancient=/root/.ethereum-ancient-chaindata")
fi

if [[ $NETWORK == "testnet" ]]; then
  OPTS+=("--testnet")
fi

if [[ -e $PEERS ]]; then
  OPTS+=("--bootnodes=$(paste -sd ',' $PEERS)")
else
  case $NETWORK in
  testnet)
    OPTS+=("--bootnodes=$(paste -sd ',' $ROPSTEN_PEERS)")
    ;;
  mainnet)
    #geth seems to overwrite bootstrap nodes with the list below, only enable with additional logic to keep this list up-to-date
    #OPTS+=("--bootnodes=$(paste -sd ',' $MAINNET_PEERS)")
    ;;
  esac
fi

#shellcheck disable=SC2068
exec geth ${OPTS[@]} $@
