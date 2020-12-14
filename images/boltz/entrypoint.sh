#!/bin/bash

CHAIN=$1
DATADIR="/root/.boltz/$CHAIN"

LOGFILE="$DATADIR/boltz.log"
CONFIGFILE="$DATADIR/boltz.conf"
DATABASEFILE="$DATADIR/boltz.db"
ADMINMACAROONFILE="$DATADIR/admin.macaroon"
TLSKEYFILE="$DATADIR/tls.key"
TLSCERTFILE="$DATADIR/tls.cert"

case "$CHAIN" in
    "bitcoin")
        LOGPREFIX="BTC"

        LNDDIR="lndbtc"
        LNDHOST="lndbtc"

        PORT="9002"
        RESTPORT="9003"
        ;;

    "litecoin")
        LOGPREFIX="LTC"

        LNDDIR="lndltc"
        LNDHOST="lndltc"

        PORT="9102"
        RESTPORT="9103"
        ;;

    *)
        echo "Chain $CHAIN not supported"
        exit 1
        ;;
esac

CERTPATH="/root/.$LNDDIR/tls.cert"
MACAROONPATH="/root/.$LNDDIR/data/chain/$CHAIN/$NETWORK/admin.macaroon"

write_config() {
    echo "Creating config for $CHAIN daemon"
    mkdir -p $DATADIR
    cp /sample-config.toml $CONFIGFILE

    LNDPORT="10009"

    sed -i "1s/^/logprefix=\"[$LOGPREFIX] \"\n\n/" $CONFIGFILE

    sed -i "/\[LND/,/^$/s/host.*/host = \"$LNDHOST\"/" $CONFIGFILE
    sed -i "/\[LND/,/^$/s/port.*/port = $LNDPORT/" $CONFIGFILE
    sed -i "/\[LND/,/^$/s|macaroon.*|macaroon = \"$MACAROONPATH\"|" $CONFIGFILE
    sed -i "/\[LND/,/^$/s|certificate.*|certificate = \"$CERTPATH\"|" $CONFIGFILE

    sed -i '/\[RPC/,/^$/s/host.*/host = "0.0.0.0"/' $CONFIGFILE
    sed -i "/\[RPC/,/^$/s/port.*/port = $PORT/" $CONFIGFILE

    sed -i '/\[RPC/,/^$/s/restHost.*/restHost = "0.0.0.0"/' $CONFIGFILE
    sed -i "/\[RPC/,/^$/s/restPort.*/restPort = $RESTPORT/" $CONFIGFILE
}

# Config file migration
# If the config file does *not* contain anything related to the REST proxy of boltz-lnd,
# it is safe to assume that it is oudated and needs to be recreated
if [[ -e $CONFIGFILE ]] && ! grep -q "rest" "$CONFIGFILE"; then
    echo "Removing outdated config file"
    rm $CONFIGFILE
fi

if [[ $REWRITE_CONFIG || ! -e $CONFIGFILE ]]; then
	write_config
fi

while ! test -f $MACAROONPATH; do
    echo "Waiting for $CHAIN LND macaroon: $MACAROONPATH"
    sleep 10
done

echo 'Detecting localnet IP for lndbtc...'
LNDBTC_IP=$(getent hosts lndbtc | awk '{ print $1 }')
echo "$LNDBTC_IP lndbtc" >> /etc/hosts

echo 'Detecting localnet IP for lndltc...'
LNDLTC_IP=$(getent hosts lndltc | awk '{ print $1 }')
echo "$LNDLTC_IP lndltc" >> /etc/hosts

exec boltzd --configfile $CONFIGFILE --logfile $LOGFILE --database.path $DATABASEFILE --rpc.adminmacaroonpath $ADMINMACAROONFILE --rpc.tlscert $TLSCERTFILE --rpc.tlskey $TLSKEYFILE
