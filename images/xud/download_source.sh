#!/bin/bash

set -euo pipefail

if [[ $1 == 'latest' ]]; then
    #branch="feat/resolver-interface"
    branch="master"
else
    branch="v$1"
fi

git clone -b $branch --depth 1 https://github.com/ExchangeUnion/xud

cd /xud

git show HEAD > git_head.txt
