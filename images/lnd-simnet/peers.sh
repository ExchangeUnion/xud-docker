#!/bin/bash
set -euo pipefail
set -m
. /wait-file.sh

lncli="lncli -n $NETWORK -c $CHAIN"
check_lnd() {
  n=$(ps | grep "lnd" | grep -v grep | wc -l)
  [ "$n" -eq "1" ] && $lncli getinfo > /dev/null 2>&1
}

connect_peers() {
  sleep 5
  PEERS_LOCK="$HOME/.lnd/peers.lock"
  wait_file "$PEERS_LOCK" && {
    echo "Connecting to bootstrap peer because $PEERS_LOCK exists."
    while ! check_lnd; do
      sleep 3
    done

    btc_peers=(
      "03a0bdf210dcecebb2d6f092b47fb7753af8114261888a365dfcb0d4548bbbdd2a@xud1.test.exchangeunion.com:10012"
      "036f9b004f047283b33a640bc4afdd26e2eb82e73938f8ac0796641ad20dc5bdd4@xud2.test.exchangeunion.com:10012"
      "023f4a4fa9166f1beb2616bf0cce2c5a4fc9fcda6d533cb760bb6630487bfafdf9@xud3.test.exchangeunion.com:10012"
    )

    ltc_peers=(
      "0270e8254e07649cdde230c9e09de6ff63c28a6d275c30b0a6863028d9db0e7c6f@xud1.test.exchangeunion.com:10011"
      "027dbb21be00a4cace0ce73761449f4d329cd400c08d556e2df4c65cf530c4e689@xud2.test.exchangeunion.com:10011"
      "03e26345aa5d7024668e1f16adc2ecd85907a930820ad5a32736946cb824067eeb@xud3.test.exchangeunion.com:10011"
    )

    if [ "$NETWORK" = "simnet" ]; then
      if [ -e index.txt ]; then
        index=$(cat index.txt)
      else
        let index="$RANDOM % 3"
        echo "$index" > index.txt
      fi
      if [ "$CHAIN" = "bitcoin" ]; then
        connectstr="${btc_peers[$index]}"
        echo "[DEBUG] Connect to peer $connectstr for inbound channel."
        $lncli connect "$connectstr"
      else
        connectstr="${ltc_peers[$index]}"
        echo "[DEBUG] Connect to peer $connectstr for inbound channel."
        $lncli connect "$connectstr"
      fi
    fi
    rm "$PEERS_LOCK"
  }
  connect_peers
}

connect_peers
