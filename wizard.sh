#!/bin/bash

network=testnet
original_dir=`pwd`

show_help() {
    cat <<EOF
Usage: $0 [-n <network>] install
       $0 [-n <network>] upgrade
       $0 [-n <network>] report
EOF
    exit 0
}

while getopts "hn:" opt; do
    case "$opt" in
    h)
        show_help
        ;;
    n)
        network=$OPTARG
        ;;
    esac
done
shift $((OPTIND -1))

home=~/.xud-docker/$network

if ! [ -e $home ]; then
    mkdir -p $home
fi

cd $home

download_docker_compose_yml() {
    if [ -e docker-compose.yml ]; then
        echo "docker-compose.yml exists"
        rm docker-compose.yml
    fi
    curl https://raw.githubusercontent.com/ExchangeUnion/xud-docker/master/xud-$network/docker-compose.yml > docker-compose.yml
}

upgrade() {
    docker-compose down \
    && download_docker_compose_yml \
    && docker-compose pull \
    && docker-compose up -d
}

install() {
    if [ -e docker-compose.yml ]; then
        read -p "Already installed. Would you like to upgrade? (y/n) " -n 1 -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            upgrade
        fi
        return
    fi
    download_docker_compose_yml \
    && docker-compose up -d
}

report() {
    docker-compose ps >> report.txt
    docker-compose logs bitcoind >> report.txt
    docker-compose logs litecoind >> report.txt
    docker-compose logs lndbtc >> report.txt
    docker-compose logs lndltc >> report.txt
    docker-compose logs geth >> report.txt
    docker-compose logs raiden >> report.txt
    docker-compose logs xud >> report.txt
}

if [ -z $1 ]; then
    show_help
fi

eval $1