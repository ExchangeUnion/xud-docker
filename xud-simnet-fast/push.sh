#!/bin/bash

docker tag xud-simnet-fast_btcd exchangeunion/btcd-simnet
docker tag xud-simnet-fast_ltcd exchangeunion/ltcd-simnet
docker tag xud-simnet-fast_lndbtc exchangeunion/lnd
docker tag xud-simnet-fast_xud exchangeunion/xud:test

docker push exchangeunion/btcd-simnet
docker push exchangeunion/ltcd-simnet
docker push exchangeunion/lnd
docker push exchangeunion/xud:test
