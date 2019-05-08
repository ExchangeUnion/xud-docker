#!/bin/bash

echo "Compress btcd data"
tar -c -f xud-simnet2/btcd/data.tar.gz -z -v -C data/btcd/data/simnet/blocks_ffldb .

echo "Compress ltcd data"
tar -c -f xud-simnet2/ltcd/data.tar.gz -z -v -C data/ltcd/data/simnet/blocks_ffldb .
