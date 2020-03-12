#!/bin/bash

set -o errexit # -e
set -o nounset # -u
set -o pipefail
set -o monitor # -m

XUD_DIR=$HOME/.xud
TOR_DIR=$XUD_DIR/tor
TOR_DATA_DIR=$XUD_DIR/tor-data
LND_HOSTNAME="$TOR_DIR/hostname"
P2P_PORT=28885

[[ -e /app ]] || {
    mkdir /app
    tar -xf /app.tar.xz -C /app
    [ -e /usr/local/bin/xucli ] || ln -s /app/bin/xucli /usr/local/bin/xucli
    [ -e /usr/local/bin/xud ] || ln -s /app/bin/xud /usr/local/bin/xud
}

[[ -e /etc/tor/torrc ]] || cat <<EOF >/etc/tor/torrc
DataDirectory $TOR_DATA_DIR
ExitPolicy reject *:* # no exits allowed
HiddenServiceDir $TOR_DIR
HiddenServicePort $P2P_PORT 127.0.0.1:$P2P_PORT
HiddenServiceVersion 3
EOF

tor -f /etc/tor/torrc &

while [[ ! -e $LND_HOSTNAME ]]; do
    echo "[DEBUG] Waiting for xud onion address"
    sleep 1
done

XUD_ADDRESS=$(cat "$LND_HOSTNAME")
echo "[DEBUG] Onion address for xud is $XUD_ADDRESS"

while [[ ! -e "/root/.lndbtc/data/chain/bitcoin/$NETWORK/admin.macaroon" ]]; do
    echo "Waiting for lndbtc admin.macaroon"
    sleep 3
done

while ! [ -e "/root/.lndltc/data/chain/litecoin/$NETWORK/admin.macaroon" ]; do
    echo "Waiting for lndltc admin.macaroon"
    sleep 3
done

echo 'Detecting localnet IP for lndbtc...'
LNDBTC_IP=$(getent hosts lndbtc | awk '{ print $1 }')
echo "$LNDBTC_IP lndbtc" >> /etc/hosts

echo 'Detecting localnet IP for lndltc...'
LNDLTC_IP=$(getent hosts lndltc | awk '{ print $1 }')
echo "$LNDLTC_IP lndltc" >> /etc/hosts

echo 'Detecting localnet IP for raiden...'
RAIDEN_IP=$(getent hosts raiden | awk '{ print $1 }')
echo "$RAIDEN_IP raiden" >> /etc/hosts

XUD_CONF=$XUD_DIR/xud.conf
[[ -e $XUD_CONF && $PRESERVE_CONFIG == "true" ]] || {
    cp /app/sample-xud.conf $XUD_CONF
    sed -i "s/network.*/network = \"$NETWORK\"/" $XUD_CONF
    sed -i '/\[http/,/^$/s/host.*/host = "0.0.0.0"/' $XUD_CONF
    sed -i '/\[lnd\.BTC/,/^$/s/host.*/host = "lndbtc"/' $XUD_CONF
    sed -i "/\[lnd\.BTC/,/^$/s|^$|certpath = \"/root/.lndbtc/tls.cert\"\nmacaroonpath = \"/root/.lndbtc/data/chain/bitcoin/$NETWORK/admin.macaroon\"\n|" $XUD_CONF
    sed -i '/\[lnd\.LTC/,/^$/s/host.*/host = "lndltc"/' $XUD_CONF
    sed -i '/\[lnd\.LTC/,/^$/s/port.*/port = 10009/' $XUD_CONF
    sed -i "/\[lnd\.LTC/,/^$/s|^$|certpath = \"/root/.lndltc/tls.cert\"\nmacaroonpath = \"/root/.lndltc/data/chain/litecoin/$NETWORK/admin.macaroon\"\n|" $XUD_CONF
    sed -i "/\[p2p/,/^$/s/addresses.*/addresses = \[\"$XUD_ADDRESS\"]/" $XUD_CONF
    sed -i "/\[p2p/,/^$/s/port.*/port = $P2P_PORT/" $XUD_CONF
    sed -i '/\[p2p/,/^$/s/tor = .*/tor = true/' $XUD_CONF
    sed -i '/\[p2p/,/^$/s/torport.*/torport = 9050/' $XUD_CONF
    sed -i '/\[raiden/,/^$/s/host.*/host = "raiden"/' $XUD_CONF
    sed -i '/\[rpc/,/^$/s/host.*/host = "0.0.0.0"/' $XUD_CONF
}

xud $@
