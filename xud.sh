#!/bin/bash

# Fail-fast
set -e

network=testnet
original_dir=`pwd`

show_help() {
    cat <<EOF
Usage: $0 [-n <network>]

Options:
    -n Network. Available values are regtest, simnet, testnet, and mainnet. Default value is testnet
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
if ! which docker > /dev/null; then
    echo '[ERROR] docker missing'
    exit 1
fi

# Check docker-compose
if ! which docker-compose > /dev/null; then
    echo '[ERROR] docker-compose missing'
    exit 1
fi

download_docker_compose_yml() {
    echo "Download docker-compose.yml from github"
    if [ -e docker-compose.yml ]; then
        echo "docker-compose.yml exists"
        rm docker-compose.yml
    fi
    curl -s https://raw.githubusercontent.com/ExchangeUnion/xud-docker/master/xud-$network/docker-compose.yml > docker-compose.yml
}

setup_aliases() {
    echo "Set up aliases.sh from github"
    cd $root
    rm -f aliases.sh
    curl -s https://raw.githubusercontent.com/ExchangeUnion/xud-docker/master/aliases.sh > aliases.sh

    if ! [ -e ~/.bashrc ]; then
        touch ~/.bashrc
    fi

    if ! grep 'Add xud-docker aliases' ~/.bashrc; then
        cat <<EOF >> ~/.bashrc
# Add xud-docker aliases
source $root/aliases.sh
EOF
    fi
}

upgrade() {
    echo "Upgrading..."
    docker-compose down
    download_docker_compose_yml
    docker-compose pull
    docker-compose up -d
    setup_aliases
}

install() {
    echo "Installing..."
    if [ -e docker-compose.yml ]; then
        read -p "Already installed. Would you like to upgrade? (y/n) " -n 1 -r
        echo # move to a new line
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            upgrade
        fi
        return
    fi
    download_docker_compose_yml
    docker-compose up -d
    setup_aliases
    echo "XUD started successfully. Please run source ~/.bashrc and then xucli getinfo to get the status of the system. xucli help to show all available commands."
}

bug_report() {
    report="bug_report_${date +%s}.txt"
    echo "Generating $report..."
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

    for cmd in "${command[@]}"; do
        echo $cmd >> $report
        eval $cmd >> $report
        echo "" >> $report
    done
}

launch_xud_shell() {
    docker-compose exec xud bash
}

restart_all_containers() {
    docker-compose down
    docker-compose up -d
}

get_up_services() {
    IFS=$'\n'
    docker-compose ps | grep Up | awk '{print $1}' | sed "s/$network_//g" | sed "s/_1//g"
}

is_ready() {
    services=`get_up_services`
    if [ "${#services[@]}" -eq 7 ]; then
        return true
    else
        return false
    fi
}

get_status() {
    cat $home/status
}

detect_cluster_status() {
    if [ -e $home ]; then
        if is_ready; then
            echo UP
        else
            if [ `get_status` = DOWN ]; then
                echo ERROR
            else
                echo DOWN
            fi
        fi
    else 
        echo PRISTINE
    fi
}

smart_run() {
    status=`detect_cluster_status`
    echo $status > $home/status
    case $status in
        PRISTINE)
            install
            ;;
        UP)
            launch_xud_shell
            ;;
        DOWN)
            restart_all_containers
            ;;
        ERROR)
            bug_report
            ;;
    esac
}

smart_run