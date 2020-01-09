#!/bin/bash

set -euo pipefail

cd /root/xud-simnet
if bash -x scripts/xud-simnet-install; then
    /install-raiden.sh
else
    echo "Failed to execute xud-simnet-install"
    cat /tmp/*
fi
