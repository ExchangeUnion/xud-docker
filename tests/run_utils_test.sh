#!/bin/bash

cd "$(dirname "$0")" || exit 1

HOST_HOME=""
HOST_PWD=$HOME

SCRIPT=$1
shift

docker run --rm \
-v "$PWD/utils_test:/root/tests" \
-v "$PWD/utils_test/xud-docker:/mnt/hostfs/.xud-docker" \
-e NETWORK="$NETWORK" \
-e HOST_HOME="$HOST_HOME" \
-e HOST_PWD="$HOST_PWD" \
--entrypoint python \
exchangeunion/utils:latest__service-options-test \
tests/$SCRIPT.py "$@"