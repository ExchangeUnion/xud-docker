#!/bin/bash

set -o errexit # -e
set -o nounset # -u
set -o pipefail
set -o monitor # -m

XUD_DIR=$HOME/.xud
XUD_CONF=$XUD_DIR/xud.conf
TOR_DIR=$XUD_DIR/tor
TOR_DATA_DIR=$XUD_DIR/tor-data
LND_HOSTNAME="$TOR_DIR/hostname"


case $NETWORK in
    mainnet)
        P2P_PORT=8885
        RPC_PORT=8886
        HTTP_PORT=8887
        ;;
    testnet)
        P2P_PORT=18885
        RPC_PORT=18886
        HTTP_PORT=18887
        ;;
    simnet)
        P2P_PORT=28885
        RPC_PORT=28886
        HTTP_PORT=28887
        ;;
    *)
        echo >&2 "Error: Unsupported network: $NETWORK"
        exit 1
esac


[[ -e /etc/tor/torrc ]] || cat <<EOF >/etc/tor/torrc
DataDirectory $TOR_DATA_DIR
ExitPolicy reject *:* # no exits allowed
HiddenServiceDir $TOR_DIR
HiddenServicePort $P2P_PORT 127.0.0.1:$P2P_PORT
HiddenServiceVersion 3
EOF

tor -f /etc/tor/torrc &

while [[ ! -e $LND_HOSTNAME ]]; do
    echo "[entrypoint] Waiting for xud onion address"
    sleep 1
done

XUD_ADDRESS=$(cat "$LND_HOSTNAME")
echo "[entrypoint] Onion address for xud is $XUD_ADDRESS"


echo '[entrypoint] Detecting localnet IP for lndbtc...'
LNDBTC_IP=$(getent hosts lndbtc || echo '' | awk '{ print $1 }')
echo "$LNDBTC_IP lndbtc" >> /etc/hosts

echo '[entrypoint] Detecting localnet IP for lndltc...'
LNDLTC_IP=$(getent hosts lndltc || echo '' | awk '{ print $1 }')
echo "$LNDLTC_IP lndltc" >> /etc/hosts

echo '[entrypoint] Detecting localnet IP for connext...'
CONNEXT_IP=$(getent hosts connext || echo '' | awk '{ print $1 }')
echo "$CONNEXT_IP connext" >> /etc/hosts


while [[ ! -e /root/.lndbtc/tls.cert ]]; do
    echo "[entrypoint] Waiting for /root/.lndbtc/tls.cert to be created..."
    sleep 1
done

while [[ ! -e /root/.lndltc/tls.cert ]]; do
    echo "[entrypoint] Waiting for /root/.lndltc/tls.cert to be created..."
    sleep 1
done

# start xud-backup as daemon in background
supervisord -c /supervisord.conf &

# for backward compatibility
if [[ -e $XUD_CONF ]]; then
    mv "$XUD_CONF" "$XUD_DIR/previous-xud.$(date +%s).conf"
fi

# use exec to properly respond to SIGINT
# shellcheck disable=2068
exec xud \
--network="$NETWORK" \
--noencrypt=false \
--http.host="0.0.0.0" \
--http.port="$HTTP_PORT" \
--lnd.BTC.host="lndbtc" \
--lnd.BTC.port=10009 \
--lnd.BTC.certpath="/root/.lndbtc/tls.cert" \
--lnd.BTC.macaroonpath="/root/.lndbtc/data/chain/bitcoin/$NETWORK/admin.macaroon" \
--lnd.LTC.host="lndltc" \
--lnd.LTC.port=10009 \
--lnd.LTC.certpath="/root/.lndltc/tls.cert" \
--lnd.LTC.macaroonpath="/root/.lndltc/data/chain/litecoin/$NETWORK/admin.macaroon" \
--p2p.address="$XUD_ADDRESS" \
--p2p.port="$P2P_PORT" \
--p2p.tor=true \
--p2p.torport=9050 \
--raiden.disable=true \
--rpc.host="0.0.0.0" \
--rpc.port="$RPC_PORT" \
--connext.disable=false \
--connext.host="connext" \
--connext.port=5040 \
--connext.webhookhost="xud" \
--connext.webhookport="$HTTP_PORT" \
$@
