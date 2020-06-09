#!/bin/bash

XUD_DIR=$HOME/.xud
XUD_CONF=$XUD_DIR/xud.conf
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

wait_file() {
  local file="$1"; shift
  local wait_seconds="${1:-10}"; shift # after 10 seconds we give up

  until test $((wait_seconds--)) -eq 0 -o -f "$file" ; do sleep 1; done

  ((++wait_seconds))
}

write_config() {
    echo "xud.conf not found - creating a new one..."
    cp /app/sample-xud.conf $XUD_CONF

    XUD_HOSTNAME="/root/.xud/tor/hostname"
    wait_file "$XUD_HOSTNAME" && {
        XUD_ONION_ADDRESS=$(cat $XUD_HOSTNAME)
        echo "Onion address for xud is $XUD_ONION_ADDRESS"
    }

    sed -i "s/network.*/network = \"$NETWORK\"/" $XUD_CONF
    sed -i 's/noencrypt.*/noencrypt = false/' $XUD_CONF
    sed -i '/\[http/,/^$/s/host.*/host = "0.0.0.0"/' $XUD_CONF
    sed -i "/\[http/,/^$/s/port.*/port = $HTTP_PORT/" $XUD_CONF
    sed -i '/\[lnd\.BTC/,/^$/s/host.*/host = "lndbtc"/' $XUD_CONF
    sed -i "/\[lnd\.BTC/,/^$/s|^$|certpath = \"/root/.lndbtc/tls.cert\"\nmacaroonpath = \"/root/.lndbtc/data/chain/bitcoin/$NETWORK/admin.macaroon\"\n|" $XUD_CONF
    sed -i '/\[lnd\.LTC/,/^$/s/host.*/host = "lndltc"/' $XUD_CONF
    sed -i '/\[lnd\.LTC/,/^$/s/port.*/port = 10009/' $XUD_CONF
    sed -i "/\[lnd\.LTC/,/^$/s|^$|certpath = \"/root/.lndltc/tls.cert\"\nmacaroonpath = \"/root/.lndltc/data/chain/litecoin/$NETWORK/admin.macaroon\"\n|" $XUD_CONF
    sed -i "/\[p2p/,/^$/s/addresses.*/addresses = \[\"$XUD_ONION_ADDRESS\"]/" $XUD_CONF
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

if [[ $XUD_REWRITE_CONFIG || ! -e $XUD_CONF ]]; then
	write_config
fi

echo 'Detecting localnet IP for lndbtc...'
LNDBTC_IP=$(getent hosts lndbtc | awk '{ print $1 }')
echo "$LNDBTC_IP lndbtc" >> /etc/hosts

echo 'Detecting localnet IP for lndltc...'
LNDLTC_IP=$(getent hosts lndltc | awk '{ print $1 }')
echo "$LNDLTC_IP lndltc" >> /etc/hosts

echo 'Detecting localnet IP for raiden...'
RAIDEN_IP=$(getent hosts raiden | awk '{ print $1 }')
echo "$RAIDEN_IP raiden" >> /etc/hosts

exec ./bin/xud
