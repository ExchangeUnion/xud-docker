#!/bin/bash
set -euo pipefail
set -m
. /wait-file.sh

SCRIPT_PATH=$(dirname "$0")
cd "$SCRIPT_PATH" || exit 1

LND_DIR="/root/.lnd"
mkdir -p $LND_DIR

if [[ ! -e $LND_DIR/lnd.conf ]]; then
  cp /root/lnd.conf $LND_DIR/lnd.conf
fi

NEUTRINO=${NEUTRINO:-}

if [ ! -z ${NEUTRINO} ]; then
  PEERS="[neutrino]\n"

  case $CHAIN in
    bitcoin)
      case $NETWORK in
        testnet)
          PEERS="${PEERS}neutrino.connect=159.203.125.125:18333\nneutrino.connect=64.79.152.132:18333\nneutrino.connect=167.71.109.195:18333\nneutrino.connect=178.128.0.29:18333"
          ;;
        mainnet)
          PEERS="${PEERS}neutrino.connect=69.143.97.89:8333\nneutrino.connect=73.31.42.95:8333\nneutrino.connect=96.9.244.139:8333\nneutrino.connect=138.68.244.82:8333"
          ;;
        esac
      ;;
    litecoin)
          case $NETWORK in
        testnet)
          PEERS="${PEERS}neutrino.connect=ltcd.michael1011.at:19335\nneutrino.connect=ltcd.servebeer.com:54795"
          ;;
        mainnet)
          PEERS="${PEERS}neutrino.connect=ltcd.michael1011.at:9333\nneutrino.connect=ltcd.servebeer.com:9333"
          ;;
        esac
      ;;
  esac

  echo "[DEBUG] Enabling neutrino"
  case $CHAIN in
    bitcoin)
      sed -i "s/bitcoin.node=bitcoind/bitcoin.node=neutrino\n\n${PEERS}/g" $LND_DIR/lnd.conf
      ;;
    litecoin)
      sed -i "s/litecoin.node=litecoind/litecoin.node=neutrino\n\n${PEERS}/g" $LND_DIR/lnd.conf
      ;;
  esac
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
