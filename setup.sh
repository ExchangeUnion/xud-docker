#!/usr/bin/env bash

set -euo pipefail

BRANCH=master
DEV=

function parse_args() {
    local OPTION VALUE
    while [[ $# -gt 0 ]]; do
        case $1 in
        "-b" | "--branch")
            if [[ $1 =~ = ]]; then
                VALUE=$(echo "$1" | cut -d'=' -f2)
            else
                OPTION=$1
                shift
                if [[ $# -eq 0 || $1 =~ ^- ]]; then
                    echo >&2 "❌ Missing option value: $OPTION"
                    exit 1
                fi
                VALUE=$1
            fi
            BRANCH=$VALUE
            ;;
        "--dev")
            DEV=true
            shift
            ;;
        *)
            shift
            ;;
        esac
    done
}

function choose_network() {
    while true; do
        echo "1) Simnet"
        echo "2) Testnet"
        echo "3) Mainnet"
        read -p "Please choose the network: " -r
        shopt -s nocasematch
        REPLY=$(echo "$REPLY" | awk '{$1=$1;print}') # trim whitespaces
        case $REPLY in
        1 | simnet)
            NETWORK=simnet
            ;;
        2 | testnet)
            NETWORK=testnet
            ;;
        3 | mainnet)
            NETWORK=mainnet
            ;;
        *)
            continue
            ;;
        esac
        shopt -u nocasematch
        break
    done
}

function ensure_utils_image() {
    local IMG

    if [[ $DEV == "true" ]]; then
        # use local exchangeunion/utils image
        return
    fi

    if [[ $BRANCH != "master" ]]; then
        IMG="exchangeunion/utils:latest__${BRANCH//\//-}"
    fi

    if ! docker pull "$IMG" >/dev/null 2>&1; then
        echo >&2 "❌ Failed to pull $IMG"
        exit 1
    fi

    if [[ $BRANCH != "master" ]]; then
        docker tag "$IMG" exchangeunion/utils:latest
    fi
}

function check_directory() {
    if [[ ! -d $1 ]]; then
        echo "❌ $1 is not a directory"
        exit 1
    fi

    if [[ ! -r $1 ]]; then
        echo "❌ $1 is not readable"
        exit 1
    fi

    if [[ ! -w $1 ]]; then
        echo "❌ $1 is not writable"
        exit 1
    fi
}

function ensure_directory() {
    if [[ -z $1 ]]; then
        return
    fi
    if [[ ! -e $1 ]]; then
        read -p "$1 does not exist, would you like to create this directory? [Y/n] " -n 1 -r
        if [[ -n $REPLY ]]; then
            echo
        fi
        if [[ $REPLY =~ ^[Yy[:space:]]$ || -z $REPLY ]]; then
            mkdir -p "$1"
        else
            exit 1
        fi
    fi
    check_directory "$1"
}

# shellcheck disable=SC2068
parse_args $@

ensure_utils_image

docker run --rm \
    -e PROG="$0" \
    --entrypoint args_parser \
    exchangeunion/utils \
    "$@"

choose_network

echo "🚀 Launching $NETWORK environment"

HOME_DIR=$HOME/.xud-docker
BACKUP_DIR=""

if [[ ! -e $HOME_DIR ]]; then
    mkdir "$HOME_DIR"
fi

# NETWORK_DIR and BACKUP_DIR will be evaluated after running the command below
VARS="$(docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$HOME_DIR":/root/.xud-docker \
    -e HOME_DIR="$HOME_DIR" \
    -e NETWORK="$NETWORK" \
    --entrypoint config_parser \
    exchangeunion/utils \
    "$@" || exit 1)"

eval "$VARS"

NETWORK_DIR=$(realpath "$NETWORK_DIR")

ensure_directory "$BACKUP_DIR"
ensure_directory "$NETWORK_DIR"

function generate_init_script() {
    docker run --rm -it \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v "$HOME_DIR":/root/.xud-docker \
        -v "$NETWORK_DIR":/root/.xud-docker/$NETWORK \
        -e HOME_DIR="$HOME_DIR" \
        -e NETWORK="$NETWORK" \
        -e NETWORK_DIR="$NETWORK_DIR" \
        --entrypoint python \
        exchangeunion/utils \
        -m launcher "$@"
}

set +e
generate_init_script "$@"
EXIT_CODE=$?
if [[ $EXIT_CODE -eq 130 ]]; then
    exit 130  # Ctrl-C
elif [[ $EXIT_CODE -ne 0 ]]; then
    exit 1
fi
set -e

cd "$NETWORK_DIR"
LAUNCH_ARGS="$*"
NETWORK=$NETWORK NETWORK_DIR=$NETWORK_DIR HOME_DIR=$HOME_DIR LAUNCH_ARGS=$LAUNCH_ARGS bash --init-file init.sh
