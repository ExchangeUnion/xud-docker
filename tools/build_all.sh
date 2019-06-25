#!/bin/bash

set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd $DIR

./build.sh btcoind
./build.sh litecoind
./build.sh lnd
./build.sh parity
./build.sh geth
./build.sh raiden
./build.sh xud
./build.sh btcd
./build.sh ltcd
