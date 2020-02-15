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

function get_token() {
    curl -sf "https://auth.docker.io/token?service=registry.docker.io&scope=repository:$1:pull" | sed -E 's/^.*"token":"([^,]*)",.*$/\1/g'
}

function get_image_metadata() {
    local TOKEN
    local NAME
    local TAG
    NAME=$(echo "$1" | cut -d':' -f1)
    TAG=$(echo "$1" | cut -d':' -f2)
    TOKEN=$(get_token "$NAME")
    curl -sf -H "Authorization: Bearer $TOKEN" "https://registry-1.docker.io/v2/$NAME/manifests/$TAG"
}

function get_cloud_image() {
    local RESP
    RESP=$(get_image_metadata "$1")
    if [[ -z $RESP ]]; then
        return
    fi
    RESP=$(echo "$RESP" | grep v1Compatibility | head -1 | sed 's/^.*v1Compatibility":/printf/g' || echo "")
    if [[ -z $RESP ]]; then
        return
    fi
    RESP=$(eval "$RESP")
    echo "$RESP" | sed -E 's/.*sha256:([a-z0-9]+).*/\1/g'
    echo "$RESP" | sed -E 's/.*com.exchangeunion.image.created":"([^"]*)".*/\1/g'
}

function get_local_image() {
    if ! docker image inspect -f '{{.Config.Image}}' "$1" 2>/dev/null | sed -E 's/sha256://g'; then
        return
    fi
    docker image inspect -f '{{index .Config.Labels "com.exchangeunion.image.created"}}' "$1"
}

function get_image_status() {
    # possible return values: up-to-date, outdated, newer, missing, local-only
    local LOCAL CLOUD
    local L_SHA256 C_SHA256
    local L_CREATED C_CREATED
    LOCAL=$(get_local_image "$1")
    if [[ -z $LOCAL ]]; then
        echo "missing"
        return
    fi

    CLOUD=$(get_cloud_image "$1")
    if [[ -z $CLOUD ]]; then
        echo "local-only"
        return
    fi

    L_SHA256=$(echo "$LOCAL" | sed -n '1p')
    C_SHA256=$(echo "$CLOUD" | sed -n '1p')

    if [[ $L_SHA256 == "$C_SHA256" ]]; then
        echo "up-to-date"
        return
    fi

    L_CREATED=$(echo "$LOCAL" | sed -n '2p')
    C_CREATED=$(echo "$CLOUD" | sed -n '2p')

    if [[ $L_CREATED > $C_CREATED ]]; then
        echo "newer"
    else
        echo "outdated"
    fi
}

function pull_image() {
    echo "Pulling image $1"
    if ! docker pull "$1" >/dev/null 2>&1; then
        echo >&2 "❌ Failed to pull image $1"
        exit 1
    fi
}

function retag_branch_image() {
    local IMG
    if [[ $1 =~ __ ]]; then
        IMG=$(echo "$1" | sed -E 's/__.*//g')
        if ! docker tag "$1" "$IMG" >/dev/null 2>&1; then
            echo >&2 "❌ Failed to re-tag image from $1 to $IMG"
            exit 1
        fi
    fi
}

function ensure_utils_image() {
    local P_IMG # The image to pull
    local STATUS

    if [[ $BRANCH == "master" ]]; then
        P_IMG="exchangeunion/utils:latest"
    else
        P_IMG="exchangeunion/utils:latest__${BRANCH//\//-}"
    fi

    STATUS=$(get_image_status "$P_IMG")

    case $STATUS in
        missing|outdated)
            pull_image "$P_IMG"
            ;;
    esac

    retag_branch_image "$P_IMG"
}

# shellcheck disable=SC2068
parse_branch $@

ensure_utils_image

# shellcheck disable=SC2068
# shellcheck disable=SC2086
docker run --rm \
-e PROG="$0" \
--entrypoint args_parser \
exchangeunion/utils \
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
VARS="$(docker run --rm \
-v /var/run/docker.sock:/var/run/docker.sock \
-v "$HOME_DIR":/root/.xud-docker \
-v /:/mnt/hostfs \
-e HOME_DIR="$HOME_DIR" \
-e NETWORK="$NETWORK" \
--entrypoint config_parser \
exchangeunion/utils \
$@)"

eval "$VARS"

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
exchangeunion/utils \
-m launcher $@
