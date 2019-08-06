#!/bin/bash

set -m

check_xud() {
    xucli getinfo > /tmp/xud_getinfo 2>&1
    local lndbtc_ok=`cat /tmp/xud_getinfo | grep -A2 BTC | grep error | grep '""'`
    local lndltc_ok=`cat /tmp/xud_getinfo | grep -A2 LTC | grep error | grep '""'`
    local raiden_ok=`cat /tmp/xud_getinfo | grep -A1 raiden | grep error | grep '""'`

    ! [ -z "$lndbtc_ok" ] && ! [ -z "$lndltc_ok" ] && ! [ -z "$raiden_ok" ]
}

set_weth() {
    while ! check_xud; do
        sleep 3
    done

    pairs=`xucli listpairs --json|grep "/" |wc -l`

    if [ $pairs -eq 4 ] ; then
	    return
    fi

    WETH="0x9F50cEA29307d7D91c5176Af42f3aB74f0190dD3"
    DAI="0x76671A2831Dc0aF53B09537dea57F1E22899655d"

    xucli removepair WETH/BTC > /dev/null 2>&1
    xucli removepair BTC/DAI > /dev/null 2>&1
    xucli removepair LTC/DAI > /dev/null 2>&1

    xucli removecurrency WETH > /dev/null 2>&1
    xucli removecurrency DAI > /dev/null 2>&1

    xucli addcurrency WETH Raiden 18 $WETH > /dev/null 2>&1
    xucli addcurrency DAI Raiden 18 $DAI > /dev/null 2>&1

    xucli addpair WETH BTC > /dev/null 2>&1
    xucli addpair BTC DAI > /dev/null 2>&1
    xucli addpair LTC DAI > /dev/null 2>&1

    xucli listpairs
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

if [ "$NETWORK" = "simnet" ]; then
    set_weth &
fi

./bin/xud $@
