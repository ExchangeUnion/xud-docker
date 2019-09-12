#!/bin/bash
set -m

touch /root/.ethereum/passphrase.txt

./create-account.sh &

exec geth $@ --rpcaddr "$(hostname -i)"
