#!/bin/sh

while [ ! -e /root/.xud/tls.cert ]; do
    echo "[entrypoint] Waiting for xud tls.cert to be created..."
    sleep 3
done

while [ ! -e /root/.lndbtc/tls.cert ]; do
    echo "[entrypoint] Waiting for lndbtc tls.cert to be created..."
    sleep 3
done

while [ ! -e /root/.lndltc/tls.cert ]; do
    echo "[entrypoint] Waiting for lndltc tls.cert to be created..."
    sleep 3
done

if [ ! -e /root/.proxy/tls.cert ]; then
    openssl req -newkey rsa:2048 -nodes -keyout /root/.proxy/tls.key -x509 -days 1095 -subj '/CN=localhost' -out /root/.proxy/tls.crt
fi

#shellcheck disable=2068
exec proxy $@
