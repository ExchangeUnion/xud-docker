#!/bin/bash

set -euo pipefail

branch=main-log-file-fix

while getopts b: opt 2>/dev/null; do
    case "$opt" in
        b) branch=$OPTARG;;
    esac
done

bash <(curl -sf https://raw.githubusercontent.com/ExchangeUnion/xud-docker/$branch/setup.sh) $@
