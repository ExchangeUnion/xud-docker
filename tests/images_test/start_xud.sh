#!/bin/bash

BRANCH=$(git rev-parse --abbrev-ref HEAD)
BRANCH=${BRANCH//\//-}

docker run --rm -it \
-v "$PWD/data/xud:/root/.tor" \
--name xud \
"exchangeunion/xud:latest__$BRANCH" "$@"