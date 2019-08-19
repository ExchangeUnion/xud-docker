#!/bin/bash
set -euo pipefail
set -m
. /wait-file.sh

unlock_wallet() {
  sleep 5
  WALLET_LOCK="$HOME/.lnd/wallet.lock"
  wait_file "$WALLET_LOCK" && {
    echo "Trying to unlock wallet because $WALLET_LOCK exists."
    WALLET_PATH="$HOME/.lnd/data/chain/$CHAIN/$NETWORK/wallet.db"
    if [[ ! -e $WALLET_PATH ]]; then
      /wallet.exp
    fi
    /unlock.exp
    # TODO make sure wallet has been unlocked
    rm "$WALLET_LOCK"
    echo "Wallet unlocked!"
  }
  unlock_wallet
}

unlock_wallet
