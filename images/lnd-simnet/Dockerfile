FROM xud-simnet as build

FROM exchangeunion/lnd
COPY --from=build /root/xud-simnet/go/bin/lnd /root/xud-simnet/go/bin/lncli /usr/local/bin/
