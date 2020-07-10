#!/usr/bin/env bash

set -euo pipefail

docker pull exchangeunion/launcher >/dev/null

docker run --rm -it \
-v /var/run/docker.sock:/var/run/docker.sock \
-v /:/mnt/hostfs \
-e HOST_PWD="$PWD" \
-e HOST_HOME="$HOME" \
exchangeunion/launcher "$@"
