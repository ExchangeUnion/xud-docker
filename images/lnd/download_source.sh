#!/bin/bash

set -euo pipefail

if [[ $1 == 'latest' ]]; then
    git clone -b master https://github.com/lightningnetwork/lnd $GOPATH/src/github.com/lightningnetwork/lnd
else
    git clone -b v$1 https://github.com/lightningnetwork/lnd $GOPATH/src/github.com/lightningnetwork/lnd
fi
