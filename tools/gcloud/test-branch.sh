#!/bin/bash

BRANCH="$1"

git clone -b $BRANCH https://github.com/ExchangeUnion/xud-docker.git

cd ~/xud-docker

git submodule update --init

images=$(cat "xud-$NETWORK/docker-compose.yml" | grep -A 999 services | grep -A 1 -E '^  [a-z]*:' | sed -E 's/ +//g' \
| sed -E 's/image://g' | sed -E '/--/d' | sed '1d;n;d' | sed 's|exchangeunion/||g' | sed -E 's/^(.+):(.*)$/\1/g' \
| sort | uniq | paste -sd ' ' -)

for image in $images; do
  tools/build $image
done

./xud.sh -b "$BRANCH"

