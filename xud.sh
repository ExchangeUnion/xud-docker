#!/bin/bash

# Fail-fast
set -e

network=testnet
branch=master
debug=false

show_help() {
    cat <<EOF
Usage: $0 [-n <network>]

Options:
    -n Network. Available values are regtest, simnet, testnet, and mainnet. Default value is testnet
EOF
    exit 0
}

while getopts "hndb:" opt; do
    case "$opt" in
    h) 
        show_help ;;
    n) 
        network=$OPTARG ;;
    d) 
        debug=true ;;
    b) 
        branch=$OPTARG ;;
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
if ! which docker > /dev/null; then
    echo '[ERROR] docker missing'
    exit 1
fi

# Check docker-compose
if ! which docker-compose > /dev/null; then
    echo '[ERROR] docker-compose missing'
    exit 1
fi

bug_report() {
    report="bug_report_$(date +%s).txt"
    echo "Generating $home/$report..."
    commands=(
        "uname -a"
        "docker info"
        "docker stats --no-stream"
        "docker-compose ps"
        "docker-compose logs --tail=100 bitcoind"
        "docker-compose logs --tail=100 litecoind"
        "docker-compose logs --tail=100 lndbtc"
        "docker-compose logs --tail=100 lndltc"
        "docker-compose logs --tail=100 geth"
        "docker-compose logs --tail=100 raiden"
        "docker-compose logs --tail=100 xud"
    )

    for cmd in "${commands[@]}"; do
        echo $cmd >> $report
        eval $cmd >> $report
        echo "" >> $report
    done
}

launch_xud_shell() {
    cat ../banner.txt
    bash --init-file ../init.sh
}

get_up_services() {
    IFS=$'\n'
    docker-compose ps | grep Up | awk '{print $1}' | sed "s/${network}_//g" | sed "s/_1//g"
}

has_installed() {
    [ -f $home/docker-compose.yml ]
}

fetch_github_metadata() {
    export PYTHONIOENCODING=utf8
    url=`curl -s https://api.github.com/repos/ExchangeUnion/xud-docker/git/refs/heads/$branch | \
        python -c "import sys,json; print(json.load(sys.stdin)['object']['url'])"`
    ending=`curl -s $url | python -c "\
import sys,json; \
r = json.load(sys.stdin); \
print('# date: %s' % r['author']['date']); \
print('# sha: %s' % r['sha'])"`
}

download_files() {
    curl -s https://raw.githubusercontent.com/ExchangeUnion/xud-docker/$branch/xud-$network/docker-compose.yml > docker-compose.yml
    echo -e "\n$ending" >> docker-compose.yml
    curl -s https://raw.githubusercontent.com/ExchangeUnion/xud-docker/$branch/banner.txt > ../banner.txt
    curl -s https://raw.githubusercontent.com/ExchangeUnion/xud-docker/$branch/init.sh > ../init.sh
    curl -s https://raw.githubusercontent.com/ExchangeUnion/xud-docker/$branch/status.sh > ../status.sh
    chmod u+x ../status.sh
}

install() {
    $debug && return
    fetch_github_metadata
    download_files
    docker-compose up -d
}

upgrade() {
    $debug && return
    fetch_github_metadata
    a=`echo -e "$ending" | tail -1`
    b=`cat docker-compose.yml | tail -1`
    if ! [ "$a" = "$b" ]; then
        echo "New version detected, upgrading..."
        docker-compose down
        download_files
        docker-compose pull
        docker-compose up -d
    fi
}

is_all_containers_up() {
    services=(`get_up_services`)
    n="${#services[@]}"
    [ $n -eq 7 ]
}

smart_run() {
    if has_installed; then
        upgrade
    else
        install
    fi

    if ! is_all_containers_up; then
        echo "Some containers are down"
        docker-compose up -d
        echo "Wait 10 seconds to see if we can bring up all containers"
        sleep 10
        if ! is_all_containers_up; then
            bug_report
            exit 1
        fi
    fi

    launch_xud_shell
}

smart_run
