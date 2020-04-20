#!/bin/bash

set -euo pipefail
shopt -s expand_aliases
set -m

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

ADDRESS=$(get_addr)

OPTS=(
  "--rpc"
  "--accept-disclaimer"
  "--eth-rpc-endpoint $RPC_ENDPOINT"
  "--password-file $RAIDEN_DIR/passphrase.txt"
  "--datadir $RAIDEN_DIR"
  "--api-address 0.0.0.0:5001"
  "--matrix-server https://raidentransport.exchangeunion.com"
  "--address $ADDRESS"
  "--keystore-path $KEYSTORE_DIR"
)

case $NETWORK in
testnet)
  TOKEN_NETWORK_REGISTRY_ADDRESS="0x04662e916bA46bf84638daF72b067478053B6801"
  NETWORK_ID=3
  OPTS+=(
    "--network-id rinkeby"
    "--routing-mode local"
    "--environment-type production"
    "--tokennetwork-registry-contract-address $TOKEN_NETWORK_REGISTRY_ADDRESS"
    "--secret-registry-contract-address 0x2e48605E12a36bC4B9e2DA59c8b18124c06D8b2d"
    "--service-registry-contract-address 0xddFecc25B8F834D14601A7e2359FB25189994cEE"
    "--user-deposit-contract-address 0x3A17B96809258523c4DED8e7F3f9364D13eBc2C5"
    "--monitoring-service-contract-address 0x9F50cEA29307d7D91c5176Af42f3aB74f0190dD3"
    "--one-to-n-contract-address 0xA102879b6AE21B93432160532DeB8f0EA1C50b30"
    "--resolver-endpoint http://xud:18887/resolveraiden"
  )
  ;;
mainnet)
  TOKEN_NETWORK_REGISTRY_ADDRESS="0xd32F5E0fF172d41a20b32B6DAb17948B257aa371"
  NETWORK_ID=1
  OPTS+=(
    "--network-id mainnet"
    "--routing-mode private"
    "--environment-type production"
    "--tokennetwork-registry-contract-address $TOKEN_NETWORK_REGISTRY_ADDRESS"
    "--secret-registry-contract-address 0x322681a720690F174a4071DBEdB51D86E7B9FF84"
    "--service-registry-contract-address 0x281937D366C7bCE202481c45d613F67500b93E69"
    "--user-deposit-contract-address 0x4F26957E8fd331D53DD60feE77533FBE7564F5Fe"
    "--monitoring-service-contract-address 0x37cC37D7703554183aE544391945e7D0588b7693"
    "--one-to-n-contract-address 0x3dda5BE50Af796618d9f48c021Cf0C9FD64FFeb1"
    "--resolver-endpoint http://xud:8887/resolveraiden"
  )
  ;;
esac

while ! geth_ready; do
  echo "Waiting for geth to be ready"
  sleep 3
done

# This funtion is from https://github.com/raiden-network/raiden/blob/2b0f074215cb7f96b4ff70b377ae109c62f667d8/raiden/utils/formatting.py#L31-L32
function pex() {
  echo ${1:2:8} | awk '{print tolower($0)}'
}

function get_db_version() {
  # python -c 'from raiden.constants import RAIDEN_DB_VERSION; print(RAIDEN_DB_VERSION)'
  # Don't know why it is so slow to import raiden.constants. So using another method:
  grep RAIDEN_DB_VERSION /opt/venv/lib/python3.7/site-packages/raiden/constants.py | grep -o '[[:digit:]]*'
}

function get_db_path() {
  echo "/root/.raiden/node_$(pex $ADDRESS)/netid_${NETWORK_ID}/network_$(pex $TOKEN_NETWORK_REGISTRY_ADDRESS)/v$(get_db_version)_log.db"
}

function create_db_link() {
  local DB_FILE
  DB_FILE="$(get_db_path)"
  while [[ ! -e "$DB_FILE" ]]; do
    echo "[xud-backup] Waiting for raiden db file at $DB_FILE"
    sleep 3
  done

  ln -sf "$DB_FILE" /root/.raiden/.xud-backup-raiden-db
}

create_db_link &

#shellcheck disable=SC2068
exec python -m raiden ${OPTS[@]} $@
