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
KEYSTORE_DIR=$HOME/.raiden/keystore


[[ -e $KEYSTORE_DIR ]] || mkdir -p "$KEYSTORE_DIR"

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

[[ $NETWORK == "simnet" ]] && while [[ ! -e "/root/.lndbtc/data/chain/bitcoin/$NETWORK/admin.macaroon" ]]; do
    echo "[entrypoint] Waiting for lndbtc admin.macaroon"
    sleep 3
done

[[ $NETWORK == "simnet" ]] && while ! [ -e "/root/.lndltc/data/chain/litecoin/$NETWORK/admin.macaroon" ]; do
    echo "[entrypoint] Waiting for lndltc admin.macaroon"
    sleep 3
done

echo '[entrypoint] Detecting localnet IP for lndbtc...'
LNDBTC_IP=$(getent hosts lndbtc || echo '' | awk '{ print $1 }')
echo "[entrypoint] $LNDBTC_IP lndbtc" >> /etc/hosts

echo '[entrypoint] Detecting localnet IP for lndltc...'
LNDLTC_IP=$(getent hosts lndltc || echo '' | awk '{ print $1 }')
echo "[entrypoint] $LNDLTC_IP lndltc" >> /etc/hosts

echo '[entrypoint] Detecting localnet IP for connext...'
CONNEXT_IP=$(getent hosts connext || echo '' | awk '{ print $1 }')
echo "[entrypoint] $CONNEXT_IP connext" >> /etc/hosts


[[ -e $XUD_CONF && $PRESERVE_CONFIG == "true" ]] || {
    cp /app/sample-xud.conf $XUD_CONF

    sed -i "s/network.*/network = \"$NETWORK\"/" $XUD_CONF
    [[ $NETWORK != "simnet" ]] && sed -i 's/noencrypt.*/noencrypt = false/' $XUD_CONF
    sed -i '/\[http/,/^$/s/host.*/host = "0.0.0.0"/' $XUD_CONF
    sed -i "/\[http/,/^$/s/port.*/port = $HTTP_PORT/" $XUD_CONF
    sed -i '/\[lnd\.BTC/,/^$/s/host.*/host = "lndbtc"/' $XUD_CONF
    sed -i "/\[lnd\.BTC/,/^$/s|^$|certpath = \"/root/.lndbtc/tls.cert\"\nmacaroonpath = \"/root/.lndbtc/data/chain/bitcoin/$NETWORK/admin.macaroon\"\n|" $XUD_CONF
    sed -i '/\[lnd\.LTC/,/^$/s/host.*/host = "lndltc"/' $XUD_CONF
    sed -i '/\[lnd\.LTC/,/^$/s/port.*/port = 10009/' $XUD_CONF
    sed -i "/\[lnd\.LTC/,/^$/s|^$|certpath = \"/root/.lndltc/tls.cert\"\nmacaroonpath = \"/root/.lndltc/data/chain/litecoin/$NETWORK/admin.macaroon\"\n|" $XUD_CONF
    sed -i "/\[p2p/,/^$/s/addresses.*/addresses = \[\"$XUD_ADDRESS\"]/" $XUD_CONF
    sed -i "/\[p2p/,/^$/s/port.*/port = $P2P_PORT/" $XUD_CONF
    sed -i '/\[p2p/,/^$/s/tor = .*/tor = true/' $XUD_CONF
    sed -i '/\[p2p/,/^$/s/torport.*/torport = 9050/' $XUD_CONF
    sed -i '/\[raiden/,/^$/s/disable.*/disable = true/' $XUD_CONF
    sed -i '/\[raiden/,/^$/s/host.*/host = "raiden"/' $XUD_CONF
    sed -i "/\[raiden/,/^$/s|^$|keystorepath = \"$KEYSTORE_DIR\"\n|" $XUD_CONF
    sed -i '/\[rpc/,/^$/s/host.*/host = "0.0.0.0"/' $XUD_CONF
    sed -i "/\[rpc/,/^$/s/port.*/port = $RPC_PORT/" $XUD_CONF
    sed -i '/\[connext/,/^$/s/disable.*/disable = false/' $XUD_CONF
    sed -i '/\[connext/,/^$/s/host.*/host = "connext"/' $XUD_CONF
    sed -i '/\[connext/,/^$/s/port.*/port = 5040/' $XUD_CONF
    sed -i '/\[connext/,/^$/s/webhookhost.*/webhookhost = "xud"/' $XUD_CONF
    sed -i "/\[connext/,/^$/s/webhookport.*/webhookport = $HTTP_PORT/" $XUD_CONF
}

echo "[entrypoint] Launch with xud.conf:"
cat $XUD_CONF

[[ $NETWORK != "simnet" ]] && /xud-backup.sh &

# use exec to properly respond to SIGINT
exec xud $@
