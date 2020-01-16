#!/bin/bash

RAIDEN_DB_PATH="/root/.raiden/.xud-backup-raiden-db"

if [[ -d /root/.xud-backup ]]; then
    ./bin/xud-backup -b /root/.xud-backup --raiden.dbpath="$RAIDEN_DB_PATH"
else
    perl -MPOSIX -e '$0="xud-backup"; pause'
fi
