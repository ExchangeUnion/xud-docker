#!/bin/sh

while [ ! -e /root/.xud/tls.cert ]; do
    echo "[entrypoint] Waiting for xud tls.cert to be created..."
    sleep 3
done

#shellcheck disable=2068
exec proxy $@
