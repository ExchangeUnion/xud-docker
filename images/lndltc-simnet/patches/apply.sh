#!/bin/sh

set -e

git apply /patches/limits.patch
git apply /patches/fundingmanager.patch
patch lnd.go /patches/lnd.patch
patch vendor/github.com/ltcsuite/neutrino/blockmanager.go /patches/neutrino.patch
sed -i.bak "s/\!w.isDevEnv/w.isDevEnv/" vendor/github.com/ltcsuite/ltcwallet/wallet/wallet.go
