#!/bin/bash

BACKUP_DIR_VALUE_PATH="/root/.xud/.backup-dir-value"

while [[ ! -e $BACKUP_DIR_VALUE_PATH ]]; do
    echo "[xud-backup] Waiting for backup_dir value"
    sleep 1
done

BACKUP_DIR=$(cat "$BACKUP_DIR_VALUE_PATH")

function check_backup_dir() {
    if [[ ! -e $1 ]]; then
        echo "[xud-backup] $BACKUP_DIR does not exist"
        return 1
    fi

    if [[ ! -d $1 ]]; then
        echo "[xud-backup] $BACKUP_DIR is not a directory"
        return 1
    fi

    if [[ ! -r $1 ]]; then
        echo "[xud-backup] $BACKUP_DIR is not readable"
        return 1
    fi

    if [[ ! -w $1 ]]; then
        echo "[xud-backup] $BACKUP_DIR is not writable"
        return 1
    fi

    return 0
}

while ! check_backup_dir "$BACKUP_DIR"; do
    sleep 5
done

./bin/xud-backup -b "$BACKUP_DIR" \
--lnd.BTC.host="lndbtc" \
--lnd.BTC.port=10009 \
--lnd.BTC.certpath="/root/.lndbtc/tls.cert" \
--lnd.BTC.macaroonpath="/root/.lndbtc/data/chain/bitcoin/$NETWORK/admin.macaroon" \
--lnd.LTC.host="lndltc" \
--lnd.LTC.port=10009 \
--lnd.LTC.certpath="/root/.lndltc/tls.cert" \
--lnd.LTC.macaroonpath="/root/.lndltc/data/chain/litecoin/$NETWORK/admin.macaroon"
