#!/usr/bin/env bash

set -euo pipefail

BRANCH=master

function parse_branch() {
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
        *)
            shift
        esac
    done
}

function choose_network() {
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
        echo >&2 "❌ Invalid network: $REPLY"
        exit 1
        ;;
    esac
    shopt -u nocasematch
}

function ensure_utils_image() {
    UTILS_IMAGE="exchangeunion/utils"

#    if [[ $BRANCH != "master" ]]; then
#        UTILS_IMAGE="exchangeunion/utils:latest__${BRANCH//\//-}"
#    fi
#
#    if ! docker pull "$UTILS_IMAGE" >/dev/null 2>&1; then
#        echo >&2 "Failed to pull $UTILS_IMAGE"
#        exit 1
#    fi
}

# shellcheck disable=SC2068
parse_branch $@

ensure_utils_image

# shellcheck disable=SC2068
# shellcheck disable=SC2086
docker run --rm \
-e PROG="$0" \
--entrypoint args_parser \
$UTILS_IMAGE \
$@

choose_network

echo "🚀 Launching $NETWORK environment"

HOME_DIR=$HOME/.xud-docker

if [[ ! -e $HOME_DIR ]]; then
    mkdir "$HOME_DIR"
fi

# shellcheck disable=SC2068
# shellcheck disable=SC2086
# NETWORK_DIR, BACKUP_DIR and RESTORE_DIR will be evaluated after running the command below
eval "$(docker run --rm \
-v /var/run/docker.sock:/var/run/docker.sock \
-v "$HOME_DIR":/root/.xud-docker \
-v /:/mnt/hostfs \
-e HOME_DIR="$HOME_DIR" \
-e NETWORK="$NETWORK" \
--entrypoint config_parser \
$UTILS_IMAGE \
$@)"

NETWORK_DIR=$(realpath "$NETWORK_DIR")
if [[ -n $BACKUP_DIR ]]; then
    BACKUP_DIR=$(realpath "$BACKUP_DIR")
fi
if [[ -n $RESTORE_DIR ]]; then
    RESTORE_DIR=$(realpath "$RESTORE_DIR")
fi

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

ensure_directory "$NETWORK_DIR"
ensure_directory "$BACKUP_DIR"
ensure_directory "$RESTORE_DIR"

# shellcheck disable=SC2068
# shellcheck disable=SC2086
docker run --rm -it \
--name "${NETWORK}_utils" \
-v /var/run/docker.sock:/var/run/docker.sock \
-v "$HOME_DIR":/root/.xud-docker \
-v "$NETWORK_DIR":/root/.xud-docker/$NETWORK \
-v /:/mnt/hostfs \
-e HOST_PWD="$PWD" \
-e HOME_DIR="$HOME_DIR" \
-e NETWORK="$NETWORK" \
-e NETWORK_DIR="$NETWORK_DIR" \
-e BACKUP_DIR="$BACKUP_DIR" \
-e RESTORE_DIR="$RESTORE_DIR" \
--entrypoint python \
$UTILS_IMAGE \
-m launcher $@
