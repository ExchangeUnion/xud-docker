#!/bin/bash

set -o errexit # -e
set -o nounset # -u
set -o pipefail
set -o monitor # -m

if [[ $CHAIN != "litecoin" ]]; then
    echo "[entrypoint] Invalid chain: $CHAIN"
    exit 1
fi

LND_DIR=$HOME/.lnd
TOR_DIR=$LND_DIR/tor
TOR_LOG=$LND_DIR/tor.log
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

tor -f /etc/tor/torrc >"$TOR_LOG" 2>&1 &

while [[ ! -e $LND_HOSTNAME ]]; do
    echo "[entrypoint] Waiting for lndbtc onion address"
    sleep 1
done

LND_ADDRESS=$(cat "$LND_HOSTNAME")
echo "[entrypoint] Onion address for lndbtc is $LND_ADDRESS"


function connect() {
    local key="023f670b916d8b89e362f4832f8eeca4f2d578a737c97f6fd4845bb7b584647667"
    local uri="$key@xud1.simnet.exchangeunion.com:10011"
    while true; do
        echo "[entrypoint] Connecting to $uri"
        if lncli -n simnet -c litecoin connect $uri >/dev/null 2>&1; then
            if lncli -n simnet -c litecoin listpeers | grep -q $key; then
                echo "[entrypoint] Connected to $uri"
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
