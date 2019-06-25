#!/bin/bash

set -euo pipefail

start_lnd() {
    set -m

    # macaroons is force enabled when listening on public interfaces (--no-macaroons)
    # specify 0.0.0.0:10009 instead of :10009 because `lncli -n simnet getinfo` will not work with ':10009'
    lnd --rpclisten=0.0.0.0:10009 --listen=0.0.0.0:9735 --restlisten=0.0.0.0:8080 $@ &

    sleep 3

    ./wallet.exp
    ./unlock.exp

    #fg %2
}

restart_lnd() {
    set +e
    echo "[DEBUG] Enter restart_lnd function"
    n=`ps | grep "lnd " | grep -v grep | wc -l`
    echo "[DEBUG] We got $n lnd process(es) at first"
    while [ "$n" -gt "0" ]; do
        ps | grep "lnd " | grep -v grep
        echo "[DEBUG] Sleep 10 seconds to see if we kill all lnd processes"
        sleep 10
        n=`ps | grep "lnd " | grep -v grep | wc -l`
        echo "[DEBUG] Now we got $n lnd process(es) running"
    done
    echo "[DEBUG] All lnd process has been killed"
    sleep 10
    start_lnd $@
}

check_lnd() {
    echo "[DEBUG] Enter check_lnd function"
    echo "[DEBUG] Last error log"
    echo ""
    echo ""
    cat /root/.lnd/logs/$CHAIN/$NETWORK/lnd.log | grep ERR | tail -1
    echo ""
    echo ""
    n=`ps | grep "lnd " | grep -v grep | wc -l`
    [ $n -eq "1" ] && lncli -n $NETWORK -c $CHAIN getinfo > /dev/null 2>&1
}

run() {
    start_lnd $@ &
    echo "[DEBUG] Wait 30 seconds then do regular health check"
    sleep 30
    while true; do
        if ! check_lnd; then
            restart_lnd $@
        fi
        sleep 10
    done
}

run $@
