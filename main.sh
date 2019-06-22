#!/bin/bash

set -euo pipefail

network=testnet

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
        show_help ;;
    n) 
        network=$OPTARG ;;
    esac
done
shift $((OPTIND -1))

home=`pwd`

get_all_services() {
    cat docker-compose.yml | grep -Po '^  [a-z0-9]+:$' | tr ':' ' '
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
    for s in "${services[@]}"; do
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

launch_xud_shell() {
    bash --init-file ../init.sh
}

get_up_services() {
    docker-compose ps | grep Up | awk '{print $1}' | sed "s/${network}_//g" | sed "s/_1//g"
}

is_all_containers_up() {
    up_services=(`get_up_services | sort`)
    all_services=(`get_all_services | sort`)
    [[ "${up_services[@]}" = "${all_services[@]}" ]]
}

run() {
    if ! is_all_containers_up; then
        docker-compose ps
        docker-compose up -d
        sleep 10
        if ! is_all_containers_up; then
            docker-compose ps
            bug_report
            exit 1
        fi
    fi

    launch_xud_shell
}

run