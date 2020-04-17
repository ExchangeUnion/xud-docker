#!/bin/bash

set -o errexit # -e
set -o nounset # -u
set -o pipefail
set -o monitor # -m

if [[ $CHAIN != "litecoin" ]]; then
    echo "[ERROR] Invalid chain: $CHAIN"
    exit 1
fi

LND_DIR=$HOME/.lnd
TOR_DIR=$LND_DIR/tor
TOR_DATA_DIR=$LND_DIR/tor-data
LND_HOSTNAME="$TOR_DIR/hostname"
P2P_PORT=30375

[[ -e /etc/tor/torrc ]] || cat <<EOF >/etc/tor/torrc
DataDirectory $TOR_DATA_DIR
ExitPolicy reject *:* # no exits allowed
HiddenServiceDir $TOR_DIR
HiddenServicePort $P2P_PORT 127.0.0.1:$P2P_PORT
HiddenServiceVersion 3
EOF

tor -f /etc/tor/torrc &

while [[ ! -e $LND_HOSTNAME ]]; do
    echo "[DEBUG] Waiting for lndbtc onion address"
    sleep 1
done

LND_ADDRESS=$(cat "$LND_HOSTNAME")
echo "[DEBUG] Onion address for lndbtc is $LND_ADDRESS"


function connect() {
    lncli -n simnet -c litecoin connect 023f670b916d8b89e362f4832f8eeca4f2d578a737c97f6fd4845bb7b584647667@xud1.simnet.exchangeunion.com:10011
}

(sleep 30 && connect) &


lnd --externalip=$LND_ADDRESS:$P2P_PORT \
--listen=0.0.0.0:$P2P_PORT \
--rpclisten=0.0.0.0:10009 \
--restlisten=0.0.0.0:8080 \
--tor.active \
--tor.socks=9050 \
--tor.streamisolation \
$@
