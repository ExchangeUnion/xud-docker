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
LNDBTC_IP=$(getent hosts lndbtc | awk '{ print $1 }')
echo "$LNDBTC_IP lndbtc" >> /etc/hosts

echo '[entrypoint] Detecting localnet IP for lndltc...'
LNDLTC_IP=$(getent hosts lndltc | awk '{ print $1 }')
echo "$LNDLTC_IP lndltc" >> /etc/hosts

echo '[entrypoint] Detecting localnet IP for connext...'
CONNEXT_IP=$(getent hosts connext | awk '{ print $1 }')
echo "$CONNEXT_IP connext" >> /etc/hosts


while [[ ! -e /root/.lndbtc/tls.cert ]]; do
    echo "[entrypoint] Waiting for /root/.lndbtc/tls.cert to be created..."
    sleep 1
done

while [[ ! -e /root/.lndltc/tls.cert ]]; do
    echo "[entrypoint] Waiting for /root/.lndltc/tls.cert to be created..."
    sleep 1
done


[[ -e $XUD_CONF && $PRESERVE_CONFIG == "true" ]] || {
    cp /app/sample-xud.conf $XUD_CONF

    sed -i "s/network.*/network = \"$NETWORK\"/" $XUD_CONF
    sed -i 's/noencrypt.*/noencrypt = false/' $XUD_CONF
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

/xud-backup.sh &

# use exec to properly respond to SIGINT
exec xud $@
