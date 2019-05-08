#!/bin/bash

echo "Compress lndbtc data"
tar -c -f xud-simnet2/lndbtc/data.tar.gz -z -v -C data/lndbtc/data .
md5 xud-simnet2/lndbtc/data.tar.gz

echo "Compress lndltc data"
tar -c -f xud-simnet2/lndltc/data.tar.gz -z -v -C data/lndltc/data .
md5 xud-simnet2/lndltc/data.tar.gz
