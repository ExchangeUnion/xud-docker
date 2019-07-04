#!/bin/bash

set -euo pipefail
set -E # error trap

home=${XUD_DOCKER_HOME:-~/.xud-docker}
logfile=$home/xud-docker.log

failure() {
	local lineno=$1
	local msg=$2
	echo "Failed at $lineno: $msg" >>$logfile
}

emit_error() {
    >&2 echo $1
}

branch=master
debug=false

while getopts "b:d" opt 2>/dev/null; do
    case "$opt" in
        b) branch=$OPTARG;;
        d) set -x;;
    esac
done
shift $((OPTIND -1))

check_system() {
    if ! which docker > /dev/null; then
        emit_error 'docker is missing'
        exit 1
    fi

    if ! which docker-compose > /dev/null; then
        emit_error 'docker-compose is missing'
        exit 1
    fi
}

fetch_github_metadata() {
    url=`curl -sf https://api.github.com/repos/ExchangeUnion/xud-docker/git/refs/heads/$branch 2>>$logfile | grep url | tail -1 | sed -nE 's/.* "([^"]+)".*/\1/p'`
    if [[ -z $url ]]; then
        emit_error "Failed to fetch $branch branch metadata"
        exit 1
    fi
    commit=`curl -sf $url 2>>$logfile`
    if [[ -z $commit ]]; then
        emit_error "Failed to fetch commit metadata ($url)"
        exit 1
    fi
    date=`echo "$commit" | grep date | head -1 | sed -E 's/.*: "([^"]+)".*/\1/g'`
    sha=`echo "$commit" | grep sha | head -1 | sed -E 's/.*: "([^"]+).*/\1/g'`
    revision="date: $date\nsha: $sha"
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
    docker ps --format '{{.Names}}' | cut -d'_' -f 1 | sort | uniq | grep -E 'regtest|simnet|testnet|mainnet'
}

get_existing_networks() {
    docker ps -a --format '{{.Names}}' | cut -d'_' -f 1 | sort | uniq | grep -E 'regtest|simnet|testnet|mainnet'
}

do_upgrade() {
    running_networks=(`get_running_networks`)
    existing_networks=(`get_existing_networks`)
    for n in "${running_networks[@]:-}"; do
        cd $home/$n
        echo "Shutdown $n environment"
        docker-compose down >/dev/null 2>>$logfile
    done
    download_files
    for n in "${existing_networks[@]:-}"; do
        cd $home/$n
        echo "Pull $n images"
        docker-compose pull >/dev/null 2>>$logfile
    done
    for n in "${running_networks[@]:-}"; do
        cd $home/$n
        echo "Launch $n environment"
        docker-compose up -d >/dev/null 2>>$logfile
    done
}

upgrade() {
    $debug && return
    fetch_github_metadata
    a=`echo -e "$revision" | tail -1`
    if [[ -e revision.txt ]]; then
        b=`cat revision.txt | tail -1`
    else
        b=""
    fi
    if [[ $a != $b ]]; then
        echo "New version detected, upgrading..."
        do_upgrade
    fi
}

integrity_check() {
    return 0
}

fix_content() {
    return 0
}

run() {
    check_system

    if [[ -e $home ]]; then
        cd $home
        if ! integrity_check; then
            fix_content
        fi
        echo "$(date)">$logfile
        trap 'failure ${LINENO} "$BASH_COMMAND"' ERR
        upgrade
    else
        mkdir -p $home
        touch $logfile
        cd $home
        echo "$(date)">$logfile
        trap 'failure ${LINENO} "$BASH_COMMAND"' ERR
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
                echo "Comming soon..."
                ;;
            *) echo "Invalid option: $REPLY";;
        esac
    done

    cd $home/$network

    ../main.sh -n $network -l $logfile
}

run