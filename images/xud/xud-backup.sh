#!/bin/bash

if [[ -d /root/.xud-backup ]]; then
    ./bin/xud-backup -b /root/.xud-backup --raiden.dbpath="/root/.raiden/.xud-backup-raiden-db"
else
    perl -MPOSIX -e '$0="xud-backup"; pause'
fi
