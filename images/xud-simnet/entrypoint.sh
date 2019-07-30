#!/bin/bash

set -m

wait_file() {
  local file="$1"; shift
  local wait_seconds="${1:-10}"; shift # after 10 seconds we give up

  until test $((wait_seconds--)) -eq 0 -o -f "$file" ; do sleep 1; done

  ((++wait_seconds))
}

write_config() {
  echo "xud.conf not found - creating a new one..."
  cp /tmp/xud.conf ~/.xud

  hn="$(hostname)"
  n="${hn:3}"

  if [[ -z $n ]]; then
      insid="0"
  else
      insid="$n"
  fi

  sed -i "s/<instance_id>/$insid/g" ~/.xud/xud.conf
  sed -i "s/<network>/$NETWORK/g" ~/.xud/xud.conf

  XUD_HOSTNAME="/root/.xud/tor/hostname"
  wait_file "$XUD_HOSTNAME" && {
    XUD_ONION_ADDRESS=$(cat $XUD_HOSTNAME)
    echo "Onion address for xud is $XUD_ONION_ADDRESS"
    sed -i "s/<onion_address>/$XUD_ONION_ADDRESS/g" ~/.xud/xud.conf
  }
}

if [[ $XUD_REWRITE_CONFIG || ! -e ~/.xud/xud.conf ]]; then
	write_config
fi

while ! [ -e "/root/.lndbtc/data/chain/bitcoin/$NETWORK/admin.macaroon" ]; do
  echo "Waiting for lndbtc admin.macaroon"
  sleep 3
done

while ! [ -e "/root/.lndltc/data/chain/litecoin/$NETWORK/admin.macaroon" ]; do
  echo "Waiting for lndltc admin.macaroon"
  sleep 3
done

echo 'Detecting localnet IP for lndbtc...'
LNDBTC_IP=$(getent hosts lndbtc | awk '{ print $1 }')
echo "$LNDBTC_IP lndbtc" >> /etc/hosts

echo 'Detecting localnet IP for lndltc...'
LNDLTC_IP=$(getent hosts lndltc | awk '{ print $1 }')
echo "$LNDLTC_IP lndltc" >> /etc/hosts

echo 'Detecting localnet IP for raiden...'
RAIDEN_IP=$(getent hosts raiden | awk '{ print $1 }')
echo "$RAIDEN_IP raiden" >> /etc/hosts

proxychains4 ./bin/xud
