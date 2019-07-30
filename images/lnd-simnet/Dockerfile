FROM xud-simnet as build

FROM exchangeunion/lnd
COPY --from=build /root/xud-simnet/go/bin/lnd /root/xud-simnet/go/bin/lncli /usr/local/bin/
RUN apk add --no-cache bash supervisor tor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY lnd-btc.conf /root/lnd-btc.conf
COPY lnd-ltc.conf /root/lnd-ltc.conf
COPY torrc /etc/tor/torrc
COPY peers.sh /
RUN mkdir /root/.lnd/tor
