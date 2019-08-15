#!/bin/bash
# This script is meant as a helper to build local images for development. The current
# implementation always tries to fetch the remote image first so we need to build the
# image and tag it and specify the usage in the desired docker-compose.yml
set -x
~/xud-docker/tools/build lnd
docker tag exchangeunion/lnd:0.6.1-beta exchangeunion/lnd:0.6.1-beta__local
