#!/bin/sh

btcd --simnet --txindex --rpcuser=xu --rpcpass=xu --rpclisten=:18556 --nolisten $@
