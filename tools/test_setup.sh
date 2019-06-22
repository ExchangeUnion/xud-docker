#!/bin/bash

set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

project_root="$DIR/.."

cd $project_root

home=~/.xud-docker

cp status.sh main.sh init.sh banner.txt $home

for n in regtest simnet testnet mainnet; do
    if ! [ -e $home/$n ]; then
        mkdir -p $home/$n
    fi
    cp xud-$n/docker-compose.yml $home/$n/docker-compose.yml
done

cd $home

chmod u+x main.sh status.sh

cd $project_root

./setup.sh -d
