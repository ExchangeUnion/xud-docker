#!/bin/bash

if [[ -d /root/.xud-backup ]]; then
    ./bin/xud-backup -b /root/.xud-backup
else
    perl -MPOSIX -e '$0="xud-backup"; pause'
fi
