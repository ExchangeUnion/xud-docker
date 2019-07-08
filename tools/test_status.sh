#!/bin/bash

export XUD_NETWORK=testnet
cp status.sh ~/.xud-docker
cd ~/.xud-docker/testnet && ../status.sh
