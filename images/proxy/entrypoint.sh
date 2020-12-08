#!/bin/sh

# create certificates for proxy if not exists
if [ ! -e /root/.proxy/tls.crt ]; then
    openssl req -newkey rsa:2048 -nodes -keyout /root/.proxy/tls.key -x509 -days 1095 -subj '/CN=localhost' -out /root/.proxy/tls.crt
fi

#shellcheck disable=2068
exec proxy $@
