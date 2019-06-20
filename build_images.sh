#!/bin/bash

set -euo pipefail

cd images

source versions

bitcoind_tag=exchangeunion/bitcoind:$bitcoind
litecoind_tag=exchangeunion/litecoind:$litecoind
lnd_tag=exchangeunion/lnd:$lnd
geth_tag=exchangeunion/geth:$geth
raiden_tag=exchangeunion/raiden:$raiden
xud_tag=exchangeunion/xud:$xud
xudctl_tag=exchangeunion/xudctl:$xud
parity_tag=exchangeunion/parity:$parity

echo "Build bitcoind"
docker build -t $bitcoind_tag --build-arg version=$bitcoind bitcoind

echo "Build litecoind"
docker build -t $litecoind_tag --build-arg version=$litecoind litecoind

echo "Build lnd"
docker build -t $lnd_tag --build-arg version=$lnd lnd

echo "Build geth"
docker build -t $geth_tag --build-arg version=$geth geth

echo "Build parity"
docker build -t $parity_tag --build-arg version=$parity parity

echo "Build raiden"
docker build -t $raiden_tag --build-arg version=$raiden raiden

echo "Build xud"
if [ "$xud" = "latest" ]; then
    docker build -t $xud_tag --build-arg branch=master xud
else
    docker build -t $xud_tag --build-arg branch=v$xud xud
fi


echo "Push images"
docker push $bitcoind_tag
docker push $litecoind_tag
docker push $lnd_tag
docker push $geth_tag
docker push $parity_tag
docker push $raiden_tag
docker push $xud_tag

