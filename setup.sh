#!/bin/bash

#set -euo pipefail

branch=master
debug=false

while getopts "b:d" opt 2>/dev/null; do
    case "$opt" in
        b) branch=$OPTARG;;
        d) debug=true;;
    esac
done
shift $((OPTIND -1))

check_system() {
    if ! which docker > /dev/null; then
        echo '[ERROR] docker missing'
        exit 1
    fi

    if ! which docker-compose > /dev/null; then
        echo '[ERROR] docker-compose missing'
        exit 1
    fi

    if [ -z "${XUD_DOCKER_HOME:-}" ]; then
        home=~/.xud-docker
    else
        home="$XUD_DOCKER_HOME"
    fi
}

fetch_github_metadata() {
    export PYTHONIOENCODING=utf8
    url=`curl -s https://api.github.com/repos/ExchangeUnion/xud-docker/git/refs/heads/$branch | \
        python -c "import sys,json; print(json.load(sys.stdin)['object']['url'])" 2>/dev/null`
    revision=`curl -s $url | python -c "\
import sys,json; \
r = json.load(sys.stdin); \
print('# date: %s' % r['author']['date']); \
print('# sha: %s' % r['sha'])" 2>/dev/null`
    if [ -z "$revision" ]; then
        echo "[ERROR] Failed to fetch GitHub metadata"
        exit 1
    fi
}

download_files() {
    cd $home
    echo -e "$revision" >> revision.txt
    url="https://raw.githubusercontent.com/ExchangeUnion/xud-docker/$branch"

    for n in regtest simnet testnet mainnet; do
        if ! [ -e $n ]; then
            mkdir $n
        fi
        curl -s $url/xud-$n/docker-compose.yml > $n/docker-compose.yml
    done

    curl -s $url/banner.txt > banner.txt
    curl -s $url/init.sh > init.sh
    curl -s $url/status.sh > status.sh
    curl -s $url/main.sh > main.sh
    chmod u+x status.sh main.sh
}

install() {
    $debug && return
    fetch_github_metadata
    download_files
}

get_running_networks() {
    docker ps --format '{{.Names}}' | cut -d'_' -f 1 | uniq | grep -E 'regtest|simnet|testnet|mainnet'
}

get_existing_networks() {
    docker ps -a --format '{{.Names}}' | cut -d'_' -f 1 | uniq | grep -E 'regtest|simnet|testnet|mainnet'
}

remove_old() {
    docker-compose down
}

do_upgrade() {
    running_networks=(`get_running_networks`)
    existing_networks=(`get_existing_networks`)
    for n in "${running_networks[@]}"; do
        cd $home/$n
        docker-compose down
    done
    download_files
    for n in "${existing_networks[@]}"; do
        cd $home/$n
        docker-compose pull
    done
    for n in "${running_networks[@]}"; do
        cd $home/$n
        docker-compose up -d
    done
}

upgrade() {
    $debug && return
    fetch_github_metadata
    a=`echo -e "$revision" | tail -1`
    b=`cat revision.txt 2>/dev/null| tail -1`
    if ! [ "$a" = "$b" ]; then
        echo "New version detected, upgrading..."
        do_upgrade
        pwd
    fi
}

run() {
    check_system

    if [ -e $home ]; then
        cd $home
        upgrade
    else
        mkdir -p $home
        cd $home
        install
    fi

    PS3="Please choose the network: "
    options=("Simnet" "Testnet" "Mainnet")
    select opt in "${options[@]}"; do
        case $REPLY in
            "1") network="simnet"
                break;;
            "2") network="testnet"
                break;;
            "3") network="mainnet"
                break;;
            *) echo "Invalid option $REPLY";;
        esac
    done

    cd $home/$network

    ../main.sh -n $network
}

run