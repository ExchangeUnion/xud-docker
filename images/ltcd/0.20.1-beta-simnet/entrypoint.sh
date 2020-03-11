#!/bin/bash

set -m

if [[ ! -e ~/.ltcd/ltcd.conf ]]; then
    touch ~/.ltcd/ltcd.conf
fi

# if [ -e "/data.tar.gz" ]; then
#     echo "Extract blocks data"
#     mkdir -p /root/.ltcd/data/$NETWORK/blocks_ffldb
#     tar -C /root/.ltcd/data/$NETWORK/blocks_ffldb -zxvf /data.tar.gz
#     rm /data.tar.gz
#     touch /root/.ltcd/ltcd.conf
# fi

ctl="ltcctl --simnet --rpcuser=xu --rpcpass=xu"

peer_addr=`echo "$@" | sed -E 's/.*--addpeer=([0-9\.:]+).*/\1/'`

check_ltcd() {
    $ctl getinfo > /dev/null 2>&1
}

check_chain() {
    while ! check_ltcd; do
        echo "Wait 3 seconds to let ltcd start up"
        sleep 3
    done

    local_height=`$ctl getinfo | grep blocks | sed -E 's/.*: ([0-9]+).*/\1/'`
    echo "local_height=$local_height"

    peer=`$ctl getpeerinfo | grep -A 15 "$peer_addr"`
    while [[ -z $peer ]]; do
        echo "Wait for peer: $peer_addr"
        sleep 10
        peer=`$ctl getpeerinfo | grep -A 15 "$peer_addr"`
    done

    cloud_height=`echo "$peer" | tail -1 | sed -E 's/.*: ([0-9]+).*/\1/'`
    echo "cloud_height=$cloud_height"

    if [[ $local_height -gt $cloud_height ]]; then
        $ctl stop
        rm -rf ~/.ltcd
        echo "Stopped ltcd and removed all ltcd data (for cloud chain mining safty)"
    fi
}

check_chain &

exec ltcd $@
