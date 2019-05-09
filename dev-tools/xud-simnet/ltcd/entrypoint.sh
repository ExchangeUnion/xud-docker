#!/bin/sh

ltcd --simnet --txindex --rpcuser=xu --rpcpass=xu --rpclisten=:18556 --nolisten $@

