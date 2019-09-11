#!/bin/bash
set -euo pipefail
set -m
. /wait-file.sh

SCRIPT_PATH=$(dirname "$0")
cd "$SCRIPT_PATH" || exit 1

LND_DIR="/root/.lnd"
mkdir -p $LND_DIR

if [ "$CHAIN" = "bitcoin" ]; then
  echo "[DEBUG] Using configuration for bitcoin"
  cp /root/lnd-btc.conf $LND_DIR/lnd.conf
else
  echo "[DEBUG] Using configuration for litecoin"
  cp /root/lnd-ltc.conf $LND_DIR/lnd.conf
fi

LND_HOSTNAME="$HOME/.lnd/tor/hostname"
echo "Waiting for lnd-$CHAIN onion address..."

wait_file "$LND_HOSTNAME" && {
	LND_ONION_ADDRESS=$(cat "$LND_HOSTNAME")
	echo "Onion address for lnd-$CHAIN is $LND_ONION_ADDRESS"
  # mark lnd as locked before starting
  touch "$HOME/.lnd/wallet.lock"
  # notify peers.sh to bootstrap peers
  touch "$HOME/.lnd/peers.lock"

  IP="$(hostname -i)"

  lnd --$CHAIN.$NETWORK --lnddir=$LND_DIR --externalip="$LND_ONION_ADDRESS" --listen=$IP:9735 --rpclisten=$IP:10009 --restlisten=$IP:8080
} || exit 1
