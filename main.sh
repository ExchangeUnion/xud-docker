#!/bin/bash

set -euo pipefail

network=testnet
logfile=/dev/null

show_help() {
    cat <<EOF
Usage: $0 [-n <network>]

Options:
    -n Network. Available values are regtest, simnet, testnet, and mainnet. Default value is testnet
    -l Logfile. Default value is /dev/null
EOF
    exit 0
}

while getopts "hn:l:" opt; do
    case "$opt" in
    h) 
        show_help ;;
    n) 
        network=$OPTARG ;;
    l)
        logfile=$OPTARG ;;
    esac
done
shift $((OPTIND -1))

home=`pwd`

get_all_services() {
    cat docker-compose.yml | sed -nE 's/^  ([a-z]+):$/\1/p'
}

bug_report() {
    report="bug_report_$(date +%s).txt"
    echo "Generating bug report file: $home/$report"
    
    commands=(
        "uname -a"
        "docker info"
        "docker stats --no-stream"
        "docker-compose ps"
    )
    services=(`get_all_services`)
    for s in "${services[@]:-}"; do
        commands+=("docker-compose logs --tail=100 $s")
    done

    set +e

    for cmd in "${commands[@]}"; do
        echo $cmd >> $report
        eval $cmd >> $report
        echo "" >> $report
    done

    set -e
}

check_wallet() {
    echo "Check wallet"
    return 0
}

launch_xud_shell() {
    if [[ $network == 'testnet' ]]; then
        check_wallet
    fi

    bash --init-file ../init.sh
}

get_up_services() {
    docker-compose ps | grep Up | awk '{print $1}' | sed -E "s/${network}_//g" | sed -E 's/_1//g'
}

is_all_containers_up() {
    up_services=(`get_up_services | sort`)
    all_services=(`get_all_services | sort`)
    [[ "${up_services[@]:-}" == "${all_services[@]:-}" ]]
}

run() {
    if ! is_all_containers_up; then
        echo "Launch $network environment"
        docker-compose up -d >/dev/null 2>>$logfile
        sleep 10
        if ! is_all_containers_up; then
            bug_report
            exit 1
        fi
    fi

    launch_xud_shell
}

run