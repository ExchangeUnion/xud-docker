#!/bin/bash

RAIDEN_DB_PATH="/root/.raiden/.xud-backup-raiden-db"
BACKUP_DIR_VALUE_PATH="/root/.xud/.backup-dir-value"

while [[ ! -e $BACKUP_DIR_VALUE_PATH ]]; do
    echo "[xud-backup] Waiting for backup_dir value"
    sleep 1
done

BACKUP_DIR=$(cat "$BACKUP_DIR_VALUE_PATH")

if [[ -d $BACKUP_DIR ]]; then
    ./bin/xud-backup -b "$BACKUP_DIR" --raiden.dbpath="$RAIDEN_DB_PATH"
else
    perl -MPOSIX -e '$0="xud-backup"; pause'
fi
