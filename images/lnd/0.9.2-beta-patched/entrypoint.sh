#!/bin/bash

set -o errexit # -e
set -o nounset # -u
set -o pipefail
set -o monitor # -m

if [[ $CHAIN != "bitcoin" ]]; then
    echo "[entrypoint] Invalid chain: $CHAIN"
    exit 1
fi

LND_DIR=$HOME/.lnd
TOR_DIR=$LND_DIR/tor
TOR_LOG=$LND_DIR/tor.log
TOR_DATA_DIR=$LND_DIR/tor-data
LND_HOSTNAME="$TOR_DIR/hostname"
P2P_PORT=29735

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

function connect() {
    local key="0331c98ab6ec199164130cca2b2118a17e7d5e8b53d4e46ddfd4b656a30c636b70"
    local uri="$key@5ucnksx35jjj34atausbifhyoiv7adsrjatqb5vpns6fftqaxmbvzfid.onion:29375"
    local result
    while true; do
        echo "[entrypoint] Connecting to $uri"
        if result=$(lncli -n simnet -c bitcoin connect $uri 2>&1); then
            if lncli -n simnet -c bitcoin listpeers | grep -q $key; then
                echo "[entrypoint] Connected to $uri"
                break
            fi
        else
            if echo "$result" | grep -q "cannot make connection to self"; then
                break
            fi
            if echo "$result" | grep -q "already connected to peer"; then
                break
            fi
        fi
        sleep 5
    done
}

connect &


while ! nc -z 127.0.0.1 9050; do
    echo "[entrypoint] Waiting for Tor port 9050 to be open"
    sleep 1
done

# use exec to properly respond to SIGINT
exec lnd --externalip=$LND_ADDRESS:$P2P_PORT \
--listen=0.0.0.0:$P2P_PORT \
--rpclisten=0.0.0.0:10009 \
--restlisten=0.0.0.0:8080 \
--tor.active \
--tor.socks=9050 \
--tor.streamisolation \
$@
