#!/bin/bash

RAIDEN_DB_PATH="/root/.raiden/.xud-backup-raiden-db"
BACKUP_DIR_VALUE_PATH="/root/.xud/.backup-dir-value"

while [[ ! -e $BACKUP_DIR_VALUE_PATH ]]; do
    echo "[xud-backup] Waiting for backup_dir value"
    sleep 1
done

BACKUP_DIR=$(cat "$BACKUP_DIR_VALUE_PATH")

if [[ ! -e $BACKUP_DIR ]]; then
    echo "[xud-backup] $BACKUP_DIR is not existed"
    exit 1
fi

if [[ ! -d $BACKUP_DIR ]]; then
    echo "[xud-backup] $BACKUP_DIR is not a directory"
    exit 1
fi

if [[ ! -r $1 ]]; then
    echo "[xud-backup] $BACKUP_DIR is not readable"
    exit 1
fi

if [[ ! -w $1 ]]; then
    echo "[xud-backup] $BACKUP_DIR is not writable"
    exit 1
fi

./bin/xud-backup -b "$BACKUP_DIR" --raiden.dbpath="$RAIDEN_DB_PATH"
