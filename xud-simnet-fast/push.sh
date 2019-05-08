#!/bin/bash

docker tag xud-simnet2_btcd exchangeunion/btcd-simnet
docker tag xud-simnet2_ltcd exchangeunion/ltcd-simnet
docker tag xud-simnet2_lndbtc exchangeunion/lndbtc-simnet
docker tag xud-simnet2_lndltc exchangeunion/lndltc-simnet
docker tag xud-simnet2_xud exchangeunion/xud-simnet

docker push exchnageunion/btcd-simnet
docker push exchangeunion/ltcd-simnet
docker push exchangeunion/lndbtc-simnet
docker push exchangeunion/lndltc-simnet
docker push exhcnageunion/xud-simnet
