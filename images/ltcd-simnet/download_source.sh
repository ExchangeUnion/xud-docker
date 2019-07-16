#!/bin/bash

set -euo pipefail

if [[ $1 == 'latest' ]]; then
    branch="master"
else
    branch="v$1"
fi

git clone -b $branch https://github.com/ltcsuite/ltcd $GOPATH/src/github.com/ltcsuite/ltcd
