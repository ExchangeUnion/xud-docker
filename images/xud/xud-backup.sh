#!/bin/bash

RAIDEN_DB_PATH="/root/.raiden/.xud-backup-raiden-db"

while [[ ! -e $RAIDEN_DB_PATH ]]; do
  echo "[BACKUP] Waiting for raiden db file"
  sleep 3
done

if [[ -d /root/.xud-backup ]]; then
    ./bin/xud-backup -b /root/.xud-backup --raiden.dbpath="$RAIDEN_DB_PATH"
else
    perl -MPOSIX -e '$0="xud-backup"; pause'
fi
