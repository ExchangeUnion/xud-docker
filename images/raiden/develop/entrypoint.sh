#!/bin/bash

set -o errexit # -e
set -o nounset # -u
set -o pipefail
set -o monitor # -m

source /opt/venv/bin/activate

if [[ ! -e ~/.raiden ]]; then
    mkdir ~/.raiden
fi
cd /root/.raiden

if [[ ! -e "addr.txt" ]]; then
    addr=$(python /opt/onboarder.py | tail -1 | awk '{print $2}')
    echo "$addr" > addr.txt
    echo "123123123" > password.txt
else
    addr=$(cat addr.txt)
fi

python -m raiden \
--accept-disclaimer \
--datadir /root/.raiden \
--keystore-path /root/.raiden/keystore \
--password-file /root/.raiden/password.txt \
--address $addr \
--rpc \
--api-address 0.0.0.0:5001 \
$@
