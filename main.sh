#!/bin/bash

set -euo pipefail

network=testnet
logfile=/dev/null

direct_launch=false

show_help() {
    cat <<EOF
Usage: $0 [-n <network>]

Options:
    -n Network. Available values are regtest, simnet, testnet, and mainnet. Default value is testnet
    -l Logfile. Default value is /dev/null
EOF
    exit 0
}

while getopts "hn:l:d" opt; do
    case "$opt" in
    h)
        show_help ;;
    n)
        network=$OPTARG ;;
    l)
        logfile=$OPTARG ;;
    d)
        set -x ;;
    esac
done
shift $((OPTIND -1))

if [[ $# -gt 0 && $1 == 'shell' ]]; then
    direct_launch=true
fi

home=`pwd`

get_all_services() {
    cat docker-compose.yml | tail -n +9 | sed -nE 's/^  ([a-z]+):$/\1/p' | sort | paste -sd " " -
}

log_details() {
    commands=(
        "uname -a"
        "docker info"
        "docker stats --no-stream"
        "docker-compose ps"
    )
    services=`get_all_services`
    for s in $services; do
        commands+=("docker-compose logs --tail=1000 $s")
    done

    set +e
    for cmd in "${commands[@]}"; do
        echo $cmd >> $logfile
        eval $cmd >> $logfile 2>&1
        echo "" >> $logfile
    done
    set -e
}

check_wallet() {
    echo "Checking wallets..."
    return 0
}

launch_xud_shell() {
    if [[ $network == 'testnet' ]]; then
        check_wallet
    fi

    docker-compose logs -f >> $logfile &
    bash --init-file ../init.sh
}

get_up_services() {
    # grep ${network} in case docekr-compose ps Ports column has multiple rows
    docker-compose ps | grep "$network" | grep Up | awk '{print $1}' | sed -E "s/${network}_//g" | sed -E 's/_1//g' | sort | paste -sd " " -
}

get_down_services() {
    docker-compose ps | grep "$network" | grep -v Up | awk '{print $1}' | sed -E "s/${network}_//g" | sed -E 's/_1//g' | sort | paste -sd " " -
}

is_all_containers_up() {
    up_services=`get_up_services`
    all_services=`get_all_services`
    [[ $up_services == $all_services ]]
}

safe_pull() {
    if ! docker-compose pull >/dev/null 2>>$logfile; then
        echo "Failed to pull some images"
    fi
}

launch_check() {
    if ! is_all_containers_up; then
        echo "Launching $network environment..."
        safe_pull
        docker-compose up -d >/dev/null 2>>$logfile
        sleep 10
        if ! is_all_containers_up; then
            log_details
            down_services=`get_down_services | tr ' ' ', '`
            echo "Failed to start service(s): $down_services."
            exit 1
        fi
    fi
}

run() {
    if ! $direct_launch; then
        launch_check
    fi

    launch_xud_shell
}

run $@
