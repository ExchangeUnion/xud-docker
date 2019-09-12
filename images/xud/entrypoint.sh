#!/bin/bash

set -m

check_xud() {
    xucli getinfo > /tmp/xud_getinfo 2>&1
    local lndbtc_ok=`cat /tmp/xud_getinfo | grep -A2 BTC | grep error | grep '""'`
    local lndltc_ok=`cat /tmp/xud_getinfo | grep -A2 LTC | grep error | grep '""'`
    local raiden_ok=`cat /tmp/xud_getinfo | grep -A1 raiden | grep error | grep '""'`

    ! [ -z "$lndbtc_ok" ] && ! [ -z "$lndltc_ok" ] && ! [ -z "$raiden_ok" ]
}

write_config() {
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

exec ./bin/xud $@
