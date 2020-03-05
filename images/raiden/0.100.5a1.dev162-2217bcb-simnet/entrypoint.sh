#!/bin/bash

set -euo pipefail
shopt -s expand_aliases

if [[ ! -e ~/.raiden ]]; then
    mkdir ~/.raiden
fi
cd /root/.raiden

if [[ ! -e "addr.txt" ]]; then
    addr=`python /opt/onboarder.py | tail -1 | awk '{print $2}'`
    echo "$addr" > addr.txt
    echo "123123123" > password.txt
else
    addr=`cat addr.txt`
fi

source /opt/venv/bin/activate

START_DELAY=15
sleep $START_DELAY
exec python -m raiden \
  --rpc \
  --accept-disclaimer \
  --no-sync-check \
  --address $addr \
  --keystore-path $KEYSTORE_PATH \
  --resolver-endpoint $RESOLVER_ENDPOINT \
  --eth-rpc-endpoint $ETH_RPC_ENDPOINT \
  --network-id $NETWORK_ID \
  --password-file $PASSWORD_FILE \
  --datadir $DATA_DIR \
  --api-address $API_ADDRESS \
  --environment-type $ENVIRONMENT_TYPE \
  --tokennetwork-registry-contract-address $TOKENNETWORK_REGISTRY_CONTRACT \
  --secret-registry-contract-address $SECRET_REGISTRY_CONTRACT \
  --service-registry-contract-address $SERVICE_REGISTRY_CONTRACT \
  --one-to-n-contract-address $ONE_TO_N_CONTRACT \
  --monitoring-service-contract-address $MONITORING_SERVICE_CONTRACT \
  --gas-price $GAS_PRICE \
  --matrix-server $MATRIX_SERVER \
  --routing-mode $ROUTING_MODE
