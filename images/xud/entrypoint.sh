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


if [[ -z ${LNDBTC_RPC_HOST:-} ]]; then
    LNDBTC_RPC_HOST="lndbtc"
fi
if [[ -z ${LNDBTC_RPC_PORT:-} ]]; then
    LNDBTC_RPC_PORT="10009"
fi
if [[ -z ${LNDBTC_CERTPATH:-} ]]; then
    LNDBTC_CERTPATH="/root/.lndbtc/tls.cert"
fi
if [[ -z ${LNDBTC_MACAROONPATH:-} ]]; then
    LNDBTC_MACAROONPATH="/root/.lndbtc/data/chain/bitcoin/$NETWORK/admin.macaroon"
fi

if [[ -z ${LNDLTC_RPC_HOST:-} ]]; then
    LNDLTC_RPC_HOST="lndltc"
fi
if [[ -z ${LNDLTC_RPC_PORT:-} ]]; then
    LNDLTC_RPC_PORT="10009"
fi
if [[ -z ${LNDLTC_CERTPATH:-} ]]; then
    LNDLTC_CERTPATH="/root/.lndltc/tls.cert"
fi
if [[ -z ${LNDLTC_MACAROONPATH:-} ]]; then
    LNDLTC_MACAROONPATH="/root/.lndltc/data/chain/litecoin/$NETWORK/admin.macaroon"
fi

[[ -e $XUD_CONF && $PRESERVE_CONFIG == "true" ]] || {
    cp /app/sample-xud.conf $XUD_CONF

    sed -i "s/loglevel.*/loglevel = \"trace\"/" $XUD_CONF
    sed -i "s/network.*/network = \"$NETWORK\"/" $XUD_CONF
    sed -i 's/noencrypt.*/noencrypt = false/' $XUD_CONF
    sed -i '/\[http/,/^$/s/host.*/host = "0.0.0.0"/' $XUD_CONF
    sed -i "/\[http/,/^$/s/port.*/port = $HTTP_PORT/" $XUD_CONF

    sed -i "/\[lnd\.BTC/,/^$/s/host.*/host = \"$LNDBTC_RPC_HOST\"/" $XUD_CONF
    sed -i "/\[lnd\.BTC/,/^$/s/port.*/port = $LNDBTC_RPC_PORT/" $XUD_CONF
    sed -i "/\[lnd\.BTC/,/^$/s|^$|certpath = \"$LNDBTC_CERTPATH\"\nmacaroonpath = \"$LNDBTC_MACAROONPATH\"\n|" $XUD_CONF

    sed -i "/\[lnd\.LTC/,/^$/s/host.*/host = \"$LNDLTC_RPC_HOST\"/" $XUD_CONF
    sed -i "/\[lnd\.LTC/,/^$/s/port.*/port = $LNDLTC_RPC_PORT/" $XUD_CONF
    sed -i "/\[lnd\.LTC/,/^$/s|^$|certpath = \"$LNDLTC_CERTPATH\"\nmacaroonpath = \"$LNDLTC_MACAROONPATH\"\n|" $XUD_CONF

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

function get_value() {
    sed -nE "/\[$1/,/^$/s/^.*$2 = (.+)$/\1/p" "$XUD_CONF"
}

function set_value() {
    sed -iE "/\[$1/,/^$/s|$2.*|$2 = $3|" "$XUD_CONF"
}

ARR=(
    "lnd\.BTC"  "host"          "\"$LNDBTC_RPC_HOST\""
    "lnd\.BTC"  "port"          "$LNDBTC_RPC_PORT"
    "lnd\.BTC"  "certpath"      "\"$LNDBTC_CERTPATH\""
    "lnd\.BTC"  "macaroonpath"  "\"$LNDBTC_MACAROONPATH\""

    "lnd\.LTC"  "host"          "\"$LNDLTC_RPC_HOST\""
    "lnd\.LTC"  "port"          "$LNDLTC_RPC_PORT"
    "lnd\.LTC"  "certpath"      "\"$LNDLTC_CERTPATH\""
    "lnd\.LTC"  "macaroonpath"  "\"$LNDLTC_MACAROONPATH\""
)

function update_lnds() {
    local SECTION KEY VALUE
    while [[ $# -gt 0 ]]; do
        SECTION=$1
        KEY=$2
        VALUE=$3
        shift 3
        if [[ $(get_value "$SECTION" "$KEY") != "$VALUE" ]]; then
            set_value "$SECTION" "$KEY" "$VALUE"
            echo "[entrypoint] Update $SECTION $KEY to $VALUE"
        fi
    done
}

update_lnds "${ARR[@]}"

/xud-backup.sh &


if [[ -n ${DEBUG_PORT:-} ]]; then
    export NODE_ENV=development
    exec node --inspect-brk="0.0.0.0:$DEBUG_PORT" bin/xud
else
    # use exec to properly respond to SIGINT
    exec xud "$@"
fi
