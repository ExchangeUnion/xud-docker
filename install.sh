#!/bin/bash

PS3='Please choose network: '
select network in regtest simnet testnet mainnet
do
break
done

# Check docker
if which docker > /dev/null; then
    echo '[OK] docker exists'
else
    echo '[ERROR] docker missing'
    exit 1
fi

# Check docker-compose
if which docker-compose > /dev/null; then
    echo '[OK] docker-compose exists'
else
    echo '[ERROR] docker-compose missing'
    exit 1
fi

# Check wget
if which wget > /dev/null; then
    echo '[OK] wget exists'
else
    echo '[ERROR] wget missing'
    exit 1
fi

# Download docker-compose
mkdir -p ~/.xud-docker/$network
cd ~/.xud-docker/$network

if [ -e docker-compose.yml ]; then
    docker-compose down
    rm docker-compose.yml
fi

wget https://raw.githubusercontent.com/ExchangeUnion/xud-docker/master/xud-$network/docker-compose.yml

# docker-compose up -d
docker-compose pull
docker-compose up -d
