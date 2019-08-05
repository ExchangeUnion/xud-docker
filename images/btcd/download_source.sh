#!/bin/bash

set -euo pipefail

if [[ $1 == 'latest' ]]; then
    git clone -b master https://github.com/btcsuite/btcd $GOPATH/src/github.com/btcsuite/btcd
else
    git clone -b v$1 https://github.com/btcsuite/btcd $GOPATH/src/github.com/btcsuite/btcd
fi
