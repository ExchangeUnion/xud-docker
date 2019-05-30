#!/bin/bash

PS3='Please choose network: '
options=('regtest', 'simnet', 'testnet', 'mainnet')
select opt in "${options[@]}"
do
    case $opt in
        "regtest")
            network="regtest"
            ;;
        "simnet")
            network="simnet"
            ;;
        "testnet")
            network="testnet"
            ;;
        "mainnet")
            network="mainnet"
            ;;
        *) echo "Invalid network $REPLY";;
    esac
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
wget https://raw.githubusercontent.com/ExchangeUnion/xud-docker/master/xud-$network/docker-compose.yml

# docker-compose up -d
docker-compose up -d
