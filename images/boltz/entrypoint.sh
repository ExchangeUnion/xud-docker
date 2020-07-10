#!/bin/bash

CHAIN=$1
DATADIR="/root/.boltz/$CHAIN"

LOGFILE="$DATADIR/boltz.log"
CONFIGFILE="$DATADIR/boltz.conf"
DATABASEFILE="$DATADIR/boltz.db"

case "$CHAIN" in
    "bitcoin")
        LOGPREFIX="BTC"

        LNDDIR="lndbtc"
        LNDHOST="lndbtc"

        PORT="9002"
        ;;

    "litecoin")
        LOGPREFIX="LTC"

        LNDDIR="lndltc"
        LNDHOST="lndltc"

        PORT="9003"
        ;;

    *)
        echo "Chain $CHAIN not supported"
        exit 1
        ;;
esac

CERTPATH="/root/.$LNDDIR/tls.cert"
MACAROONPATH="/root/.$LNDDIR/data/chain/$CHAIN/$NETWORK/admin.macaroon"

write_config() {
    echo "Creating new config for $CHAIN daemon"
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
}

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

exec boltzd --configfile $CONFIGFILE --logfile $LOGFILE --database.path $DATABASEFILE
