#!/bin/bash

echo "Compress btcd data"
tar -c -f btcd/data.tar.gz -z -v -C ../xud-simnet/data/btcd/data/simnet/blocks_ffldb .

echo "Compress ltcd data"
tar -c -f ltcd/data.tar.gz -z -v -C ../xud-simnet/data/ltcd/data/simnet/blocks_ffldb .
