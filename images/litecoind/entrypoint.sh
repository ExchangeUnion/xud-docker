#!/bin/bash

set -euo pipefail

LITECOIN_DIR=/root/.litecoin

if [[ $NETWORK == "testnet" ]]; then
    LOGFILE=$LITECOIN_DIR/testnet4/debug.log
elif [[ $NETWORK == "mainnet" ]]; then
    LOGFILE=$LITECOIN_DIR/debug.log
fi

ERROR=$(tail -50 $LOGFILE | grep -A 2 ReadBlockFromDisk)
if [[ -n $ERROR ]]; then
    if [[ $(echo "$ERROR" | sed -n '2p') =~ "Failed to read block" && $(echo "$ERROR" | sed -n '3p') =~ "A fatal internal error occurred" ]]; then
        # shellcheck disable=SC2068
        litecoind -reindex-chainstate $@
        exit $?
    fi
fi

# shellcheck disable=SC2068
litecoind $@