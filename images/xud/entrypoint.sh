#!/bin/bash

set -euo pipefail

XUD_DIR="$HOME/.xud"
TOR_HOSTNAME="$HOME/.tor/service/hostname"

function wait_file() {
    local FILE="$1"
    while [[ ! -e $FILE ]]; do
        sleep 1
    done
}

function wait_9050() {
    while ! nc -z tor 9050; do
        sleep 1
    done
}

function write_config() {
    cp /tmp/xud.conf $XUD_DIR
    sed -i "s/<network>/$NETWORK/g" $XUD_DIR/xud.conf
    sed -i "s/<onion_address>/$XUD_ONION_ADDRESS/g" $XUD_DIR/xud.conf
}

function resolve_ip() {
    local HOSTNAME="$1"
    getent hosts "$HOSTNAME" | awk '{ print $1 }'
}

###############################################################################

exec ./bin/xud $@
