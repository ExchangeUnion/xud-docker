#!/bin/bash
set -euo pipefail
set -m
. /wait-file.sh

SCRIPT_PATH=$(dirname "$0")
cd "$SCRIPT_PATH" || exit 1

LND_DIR="/root/.lnd"
mkdir -p $LND_DIR

cp /root/lnd.conf $LND_DIR/lnd.conf

NEUTRINO=${NEUTRINO:-}

if [ ! -z ${NEUTRINO} ]; then
  PEERS="[neutrino]\n"

  case $CHAIN in
    bitcoin)
      case $NETWORK in
        testnet)
          PEERS="${PEERS}neutrino.addpeer=bitcoin.michael1011.at:18333\nneutrino.addpeer=btc.kilrau.com:18333"
          ;;
        mainnet)
          PEERS="${PEERS}neutrino.addpeer=bitcoin.michael1011.at:8333\nneutrino.addpeer=btc.kilrau.com:8333\nneutrino.addpeer=btc.mcnally.cloud:8333"
          ;;
        esac
      ;;
    litecoin)
          case $NETWORK in
        testnet)
          PEERS="${PEERS}neutrino.connect=ltcd.michael1011.at:19335\nneutrino.connect=ltc.kilrau.com:19335"
          ;;
        mainnet)
          PEERS="${PEERS}neutrino.connect=ltcd.michael1011.at:9333\nneutrino.connect=ltc.kilrau.com:9333"
          ;;
        esac
      ;;
  esac

  echo "[DEBUG] Enabling neutrino"
  case $CHAIN in
    bitcoin)
      sed -i "s/bitcoin.node=bitcoind/bitcoin.node=neutrino\n\n${PEERS}\n\n[routing]\nrouting.assumechanvalid=1/g" $LND_DIR/lnd.conf
      ;;
    litecoin)
      sed -i "s/litecoin.node=litecoind/litecoin.node=neutrino\n\n${PEERS}\n\n[routing]\nrouting.assumechanvalid=1/g" $LND_DIR/lnd.conf
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
