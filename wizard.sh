#!/bin/bash

# Fail-fast
set -e

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
root=~/.xud-docker

if ! [ -e $home ]; then
    mkdir -p $home
fi

cd $home

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

download_docker_compose_yml() {
    echo "Download docker-compose.yml from github"
    if [ -e docker-compose.yml ]; then
        echo "docker-compose.yml exists"
        rm docker-compose.yml
    fi
    curl -S https://raw.githubusercontent.com/ExchangeUnion/xud-docker/master/xud-$network/docker-compose.yml > docker-compose.yml
}

upgrade_aliases() {
    echo "Upgrade aliases.sh from github"
    cd $root
    rm -f aliases.sh
    curl https://raw.githubusercontent.com/ExchangeUnion/xud-docker/master/aliases.sh > aliases.sh
}

upgrade() {
    echo "Upgrading..."
    docker-compose down
    download_docker_compose_yml
    docker-compose pull
    docker-compose up -d
    upgrade_aliases
}

install_aliases() {
    upgrade_aliases
    if ! [ -e ~/.bashrc ]; then
        touch ~/.bashrc
    fi
    cat <<EOF >> ~/.bashrc
# Add docker-compose aliases
source $root/aliases.sh
EOF
}

install() {
    echo "Installing..."
    if [ -e docker-compose.yml ]; then
        read -p "Already installed. Would you like to upgrade? (y/n) " -n 1 -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            upgrade
        fi
        return
    fi
    download_docker_compose_yml
    docker-compose up -d
    install_aliases
    echo "XUD started successfully. Please run source ~/.bashrc and then xucli getinfo to get the status of the system. xucli help to show all available commands."
}

report() {
    echo "Generate report.txt"
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