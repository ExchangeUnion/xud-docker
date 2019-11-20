#!/bin/bash

set -euo pipefail
shopt -s expand_aliases

#shellcheck disable=SC1091
source /opt/venv/bin/activate

RAIDEN_DIR="$HOME/.raiden"
KEYSTORE_DIR="$RAIDEN_DIR/keystore"

if [[ ! -e $RAIDEN_DIR/passphrase.txt ]]; then
  touch "$RAIDEN_DIR/passphrase.txt"
fi

RPC_ENDPOINT="${RPC_ENDPOINT:-http://geth:8545}"

function geth_ready() {
  if [[ $RPC_ENDPOINT =~ "http" ]]; then
    URL="$RPC_ENDPOINT"
  else
    URL="http://$RPC_ENDPOINT"
  fi

  curl -sf -o /dev/null -X POST -H 'Content-Type: application/json' \
    --data '{"jsonrpc":"2.0","method":"eth_syncing","params":[],"id":1}' \
    $URL
}

function get_addr() {
  local ADDR
  # UTC--2019-09-30T16-57-22.508533387Z--f7543d6e6f6567c6da42cbe9f1bb057e9303f5bd
  ADDR=$(find "$KEYSTORE_DIR" -maxdepth 1 -type f | head -1 | sed -E 's/.*--([a-z0-9]*).*/\1/g')
  # Convert the address to EIP55 checksummed address
  python -c "from web3 import Web3; print(Web3.toChecksumAddress('$ADDR'))"
}

while [[ ! -e "$KEYSTORE_DIR" || ! $(find "$KEYSTORE_DIR" -maxdepth 1 -type f | wc -l) -gt 0 ]]; do
  echo "Waiting for keystore to be generated"
  sleep 3
done

OPTS=(
  "--rpc"
  "--accept-disclaimer"
  "--resolver-endpoint http://xud:8887/resolveraiden"
  "--eth-rpc-endpoint $RPC_ENDPOINT"
  "--password-file $RAIDEN_DIR/passphrase.txt"
  "--datadir $RAIDEN_DIR"
  "--api-address 0.0.0.0:5001"
  "--matrix-server https://raidentransport.exchangeunion.com"
  "--address $(get_addr)"
  "--keystore-path $KEYSTORE_DIR"
)

case $NETWORK in
testnet)
  OPTS+=(
    "--network-id ropsten"
    "--routing-mode local"
    "--environment-type production"
    "--tokennetwork-registry-contract-address 0x04662e916bA46bf84638daF72b067478053B6801"
    "--secret-registry-contract-address 0x2e48605E12a36bC4B9e2DA59c8b18124c06D8b2d"
    "--service-registry-contract-address 0xddFecc25B8F834D14601A7e2359FB25189994cEE"
    "--user-deposit-contract-address 0x3A17B96809258523c4DED8e7F3f9364D13eBc2C5"
    "--monitoring-service-contract-address 0x9F50cEA29307d7D91c5176Af42f3aB74f0190dD3"
    "--one-to-n-contract-address 0xA102879b6AE21B93432160532DeB8f0EA1C50b30"
  )
  ;;
mainnet)
  OPTS+=(
    "--network-id mainnet"
    "--routing-mode private"
    "--environment-type production"
    "--tokennetwork-registry-contract-address 0xd32F5E0fF172d41a20b32B6DAb17948B257aa371"
    "--secret-registry-contract-address 0x322681a720690F174a4071DBEdB51D86E7B9FF84"
    "--service-registry-contract-address 0x281937D366C7bCE202481c45d613F67500b93E69"
    "--user-deposit-contract-address 0x4F26957E8fd331D53DD60feE77533FBE7564F5Fe"
    "--monitoring-service-contract-address 0x37cC37D7703554183aE544391945e7D0588b7693"
    "--one-to-n-contract-address 0x3dda5BE50Af796618d9f48c021Cf0C9FD64FFeb1"
  )
  ;;
esac

while ! geth_ready; do
  echo "Waiting for geth to be ready"
  sleep 3
done

#shellcheck disable=SC2068
exec python -m raiden ${OPTS[@]} $@
