#!/bin/bash

CHAIN=$1
DATADIR="/root/.boltz/$CHAIN"

CONFIGFILE="$DATADIR/boltz.toml"

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
    echo "Creating config file for $CHAIN daemon"
    mkdir -p $DATADIR

    LNDPORT="10009"

    echo "logprefix = \"[$LOGPREFIX] \"" >> $CONFIGFILE
    echo "" >> $CONFIGFILE

    echo "[LND]" >> $CONFIGFILE
    echo "host = \"$LNDHOST\"" >> $CONFIGFILE
    echo "port = $LNDPORT" >> $CONFIGFILE
    echo "macaroon = \"$MACAROONPATH\"" >> $CONFIGFILE
    echo "certificate = \"$CERTPATH\"" >> $CONFIGFILE
    echo "" >> $CONFIGFILE

    echo "[RPC]" >> $CONFIGFILE
    echo "host = \"0.0.0.0\"" >> $CONFIGFILE
    echo "port = $PORT" >> $CONFIGFILE
    echo "restHost = \"0.0.0.0\"" >> $CONFIGFILE
    echo "restPort = $RESTPORT" >> $CONFIGFILE
}

# Config file migration
# If the config file does *not* contain anything related to the REST proxy of boltz-lnd,
# it is safe to assume that it is oudated and needs to be recreated.
if [[ -e $CONFIGFILE ]] && ! grep -q "rest" "$CONFIGFILE"; then
    echo "Removing outdated config file"
    rm $CONFIGFILE
fi

# *Another* config file migration
# In the change moving to the "--datadir" argument the config file path is not set explicitely anymore,
# which means the daemon will search for the config file in the default location which is "$DATADIR/boltz.toml".
# Therefore, old config files need to be moved.
OLD_CONFIGFILE="$DATADIR/boltz.conf"
if [[ -e $OLD_CONFIGFILE ]]; then
    echo "Moving old config file ($OLD_CONFIGFILE) to new location: $CONFIGFILE"
    mv $OLD_CONFIGFILE $CONFIGFILE
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

exec boltzd --datadir $DATADIR
