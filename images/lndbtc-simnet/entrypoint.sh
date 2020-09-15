#!/bin/bash

set -o errexit # -e
set -o nounset # -u
set -o pipefail
set -o monitor # -m

if [[ $NETWORK != "simnet" ]]; then
    echo "[entrypoint] ERROR: NETWORK must be \"simnet\""
    exit 1
fi

if [[ $CHAIN != "bitcoin" ]]; then
    echo "[entrypoint] ERROR: CHAIN must be \"bitcoin\""
    exit 1
fi

if [[ -z ${P2P_PORT:-} ]]; then
    echo "[entrypoint] ERROR: P2P_PORT is required"
    exit 1
fi


LND_DIR=$HOME/.lnd
TOR_DIR=$LND_DIR/tor
TOR_LOG=$LND_DIR/tor.log
TOR_DATA_DIR=$LND_DIR/tor-data
LND_HOSTNAME="$TOR_DIR/hostname"


[[ -e /etc/tor/torrc ]] || cat <<EOF >/etc/tor/torrc
DataDirectory $TOR_DATA_DIR
ExitPolicy reject *:* # no exits allowed
HiddenServiceDir $TOR_DIR
HiddenServicePort $P2P_PORT 127.0.0.1:$P2P_PORT
HiddenServiceVersion 3
EOF

tor -f /etc/tor/torrc >"$TOR_LOG" 2>&1 &

while [[ ! -e $LND_HOSTNAME ]]; do
    echo "[entrypoint] Waiting for lndbtc onion address"
    sleep 1
done

LND_ADDRESS=$(cat "$LND_HOSTNAME")
echo "[entrypoint] Onion address for lndbtc is $LND_ADDRESS"

while ! nc -z 127.0.0.1 9050; do
    echo "[entrypoint] Waiting for Tor port 9050 to be open"
    sleep 1
done

# use exec to properly respond to SIGINT
# shellcheck disable=2068
exec lnd \
--lnddir="$LND_DIR" \
--tor.active \
--tor.socks=9050 \
--tor.streamisolation \
--externalip="$LND_ADDRESS:$P2P_PORT" \
$@
