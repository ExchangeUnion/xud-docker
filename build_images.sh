#!/bin/bash

cd images

source versions

bitcoind_tag=exchangeunion/bitcoind:$bitcoind
litecoind_tag=exchangeunion/litecoind:$litecoind
lnd_tag=exchangeunion/lnd:$lnd
geth_tag=exchangeunion/geth:$geth
raiden_tag=exchangeunion/raiden:$raiden
xud_tag=exchangeunion/xud:$xud
xudctl_tag=exchangeunion/xudctl:$xud

docker build -t $bitcoind_tag --build-arg version=$bitcoind bitcoind
docker build -t $litecoind_tag --build-arg version=$litecoind litecoind
docker build -t $lnd_tag --build-arg version=$lnd lnd
docker build -t $geth_tag --build-arg version=$geth geth
docker build -t $raiden_tag --build-arg version=$raiden raiden
docker build -t $xud_tag --build-arg version=$xud xud
#docker build -t $xudctl_tag --build-arg version=$xudctl xudctl

docker push $bitcoind_tag
docker push $litecoind_tag
docker push $lnd_tag
docker push $geth_tag
docker push $raiden_tag
docker push $xud_tag
#docker push $xudctl_tag