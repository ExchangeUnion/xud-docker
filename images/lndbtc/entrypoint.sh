#!/bin/bash
set -euo pipefail
set -m
. /wait-file.sh

SCRIPT_PATH=$(dirname "$0")
cd "$SCRIPT_PATH" || exit 1

LND_DIR="/root/.lnd"
LND_CONF="$LND_DIR/lnd.conf"
mkdir -p $LND_DIR

if [[ ! -e $LND_CONF ]]; then
    cp /root/lnd.conf "$LND_CONF"
fi

echo "[entrypoint] Enabling $MODE mode"
if [[ $MODE == "light" || $MODE == "neutrino" ]]; then
    sed -i "s/bitcoin.node.*/bitcoin.node=neutrino/g" "$LND_CONF"
    sed -i '/routing/,$d' "$LND_CONF"
    if [[ $NETWORK == "testnet" ]]; then
        cat <<EOF >> "$LND_CONF"
[routing]
routing.assumechanvalid=1

[neutrino]
neutrino.addpeer=bitcoin.michael1011.at:18333
neutrino.addpeer=btc.kilrau.com:18333
EOF
    elif [[ $NETWORK == "mainnet" ]]; then
        cat << EOF >> "$LND_CONF"
[routing]
routing.assumechanvalid=1

[neutrino]
neutrino.addpeer=bitcoin.michael1011.at:8333
neutrino.addpeer=btc.kilrau.com:8333
neutrino.addpeer=thun.droidtech.it:8333
EOF
    fi
elif [[ $MODE == "native" ]]; then
    sed -i '/routing/,$d' "$LND_CONF"
    sed -i "s/bitcoin.node=.*/bitcoin.node=bitcoind/g" "$LND_CONF"
    sed -i "s/rpchost.*/rpchost=bitcoind/g" "$LND_CONF"
    sed -i "s/rpcuser.*/rpcuser=xu/g" "$LND_CONF"
    sed -i "s/rpcpass.*/rpcpass=xu/g" "$LND_CONF"
    sed -i "s|zmqpubrawblock.*|zmqpubrawblock=tcp://bitcoind:28332|g" "$LND_CONF"
    sed -i "s|zmqpubrawtx.*|zmqpubrawtx=tcp://bitcoind:28333|g" "$LND_CONF"
elif [[ $MODE == "external" ]]; then
    sed -i '/routing/,$d' "$LND_CONF"
    sed -i "s/bitcoin.node=.*/bitcoin.node=bitcoind/g" "$LND_CONF"
    sed -i "s/rpchost.*/rpchost=$RPCHOST/g" "$LND_CONF"
    sed -i "s/rpcuser.*/rpcuser=$RPCUSER/g" "$LND_CONF"
    sed -i "s/rpcpass.*/rpcpass=$RPCPASS/g" "$LND_CONF"
    sed -i "s|zmqpubrawblock.*|zmqpubrawblock=$ZMQPUBRAWBLOCK|g" "$LND_CONF"
    sed -i "s|zmqpubrawtx.*|zmqpubrawtx=$ZMQPUBRAWTX|g" "$LND_CONF"
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
