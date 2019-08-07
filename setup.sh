#!/bin/bash

set -euo pipefail
set -E # error trap

home=${XUD_DOCKER_HOME:-~/.xud-docker}

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

while getopts "b:d" opt; do
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
    curl -s $url/status.py > status.py
    curl -s $url/main.sh > main.sh
    curl -s $url/pull.py > pull.py
    chmod u+x status.sh main.sh pull.py
}

install() {
    $debug && return
    fetch_github_metadata
    download_files
}

get_running_networks() {
    set +o pipefail
    docker ps --format '{{.Names}}' | cut -d'_' -f 1 | sort | uniq | grep -E 'regtest|simnet|testnet|mainnet' | paste -sd " " -
    set -o pipefail
}

get_existing_networks() {
    set +o pipefail
    docker ps -a --format '{{.Names}}' | cut -d'_' -f 1 | sort | uniq | grep -E 'regtest|simnet|testnet|mainnet' | paste -sd " " -
    set -o pipefail
}

safe_pull() {
    command="python"
    if ! which python >/dev/null 2>&1; then
        command="python3"
    fi
    if ! $command ../pull.py "$branch" "$1"; then
        echo "Failed to pull images"
        exit 1
    fi
}

do_upgrade() {
    running_networks=`get_running_networks`
    for n in $running_networks; do
        cd "$home/$n"
        echo "Shutting down $n environment..."
        # docker-compose normal output prints into stderr, so we hide redirect fd(2) to /dev/null
        docker-compose down >/dev/null 2>&1
    done
    download_files
    for n in $running_networks; do
        cd "$home/$n"
        echo "Launching $n environment..."
        safe_pull "$n"
        # docker-compose normal output prints into stderr, so we hide redirect fd(2) to /dev/null
        docker-compose up -d >/dev/null 2>&1
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
        read -p "A new version is available. Would you like to upgrade (Warning: this will restart your environment and cancel all open orders)? Y/n?" -n 1 -r
        echo    # (optional) move to a new line
        if [[ $REPLY =~ ^Y$ ]]
        then
            do_upgrade
        fi
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

    PS3="Please choose the network: "
    options=("Simnet" "Testnet" "Mainnet")
    shopt -s nocasematch
    select opt in "${options[@]}"; do
        case "$REPLY" in
            1|" 1"|" 1 "|"1 "|simnet|" simnet"|" simnet "|"simnet ") network="simnet"
                break;;
            2|" 2"|" 2 "|"2 "|testnet|" testnet"|" testnet "|"testnet ") network="testnet"
                break;;
            3|" 3"|" 3 "|"3 "|mainnet|" mainnet"|" mainnet "|"mainnet ") network="mainnet"
                break;;
            *) echo "Invalid option: \"$REPLY\"";;
        esac
    done

    logfile=$home/$network/xud-docker.log

    if [[ -e $home ]]; then
        cd $home
        if ! integrity_check; then
            fix_content
        fi
        echo "$(date)">$logfile
        trap 'failure ${LINENO} "$BASH_COMMAND"' ERR
        upgrade
    else
        mkdir -p $home/$network
        touch $logfile
        cd $home
        echo "$(date)">$logfile
        trap 'failure ${LINENO} "$BASH_COMMAND"' ERR
        install
    fi

    cd $home/$network

    opts="-n $network -l $logfile -b $branch"

    if set -o | grep xtrace | grep on >/dev/null; then
        opts="$opts -d"
    fi

    if [[ $# -gt 0 && $1 == "shell" ]]; then
        opts="$opts shell"
    fi

    if ! ../main.sh $opts; then
        echo "Failed to launch $network environment. For more details, see $logfile"
    fi
}

run "$@"
