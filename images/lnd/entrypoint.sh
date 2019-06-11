#!/bin/bash

set -m

# macaroons is force enabled when listening on public interfaces (--no-macaroons)
# specify 0.0.0.0:10009 instead of :10009 because `lncli -n simnet getinfo` will not work with ':10009'
lnd --rpclisten=0.0.0.0:10009 --listen=0.0.0.0:9735 --restlisten=0.0.0.0:8080 $@ &

sleep 3

./wallet.exp
./unlock.exp

fg %1
