#!/bin/sh

set -e

patch lnd.go /patches/lnd.patch
patch vendor/github.com/lightninglabs/neutrino/blockmanager.go /patches/neutrino.patch
sed -i.bak "s/\!w.isDevEnv/w.isDevEnv/" vendor/github.com/btcsuite/btcwallet/wallet/wallet.go
