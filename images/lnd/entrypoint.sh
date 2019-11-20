#!/bin/bash
set -euo pipefail
set -m
. /wait-file.sh

SCRIPT_PATH=$(dirname "$0")
cd "$SCRIPT_PATH" || exit 1

LND_DIR="/root/.lnd"
mkdir -p $LND_DIR

if [[ ! -e $LND_DIR/lnd.conf ]]; then
  if [ "$CHAIN" = "bitcoin" ]; then
    echo "[DEBUG] Using configuration for bitcoin"
    cp /root/lnd-btc.conf $LND_DIR/lnd.conf
  else
    echo "[DEBUG] Using configuration for litecoin"
    cp /root/lnd-ltc.conf $LND_DIR/lnd.conf
  fi
fi

set +e
[[ -n ${RPCHOST:-} ]] && sed -i "s/rpchost.*/rpchost=$RPCHOST/g" $LND_DIR/lnd.conf
[[ -n ${RPCUSER:-} ]] && sed -i "s/rpcuser.*/rpcuser=$RPCUSER/g" $LND_DIR/lnd.conf
[[ -n ${RPCPASS:-} ]] && sed -i "s/rpcpass.*/rpcpass=$RPCPASS/g" $LND_DIR/lnd.conf
[[ -n ${ZMQPUBRAWBLOCK:-} ]] && sed -i "s|zmqpubrawblock.*|zmqpubrawblock=$ZMQPUBRAWBLOCK|g" $LND_DIR/lnd.conf
[[ -n ${ZMQPUBRAWTX:-} ]] && sed -i "s|zmqpubrawtx.*|zmqpubrawtx=$ZMQPUBRAWTX|g" $LND_DIR/lnd.conf
set -e

LND_HOSTNAME="$HOME/.lnd/tor/hostname"
echo "Waiting for lnd-$CHAIN onion address..."

wait_file "$LND_HOSTNAME" && {
	LND_ONION_ADDRESS=$(cat "$LND_HOSTNAME")
	echo "Onion address for lnd-$CHAIN is $LND_ONION_ADDRESS"
  # mark lnd as locked before starting
  touch "$HOME/.lnd/wallet.lock"
  # notify peers.sh to bootstrap peers
  touch "$HOME/.lnd/peers.lock"

  case $CHAIN in
    bitcoin)
      PORT=9735
      ;;
    litecoin)
      PORT=10735
      ;;
  esac

  case $NETWORK in
    testnet)
      PORT=$((PORT + 10000))
      ;;
  esac

  if [ -z ${EXTERNAL_IP+x} ]; then
    lnd --$CHAIN.$NETWORK --lnddir=$LND_DIR --externalip="$LND_ONION_ADDRESS:$PORT" --listen="0.0.0.0:$PORT"
  else
    lnd --$CHAIN.$NETWORK --lnddir=$LND_DIR --externalip="$LND_ONION_ADDRESS:$PORT" --externalip="$EXTERNAL_IP:$PORT" --listen="0.0.0.0:$PORT"
  fi
} || exit 1
