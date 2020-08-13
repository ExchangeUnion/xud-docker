#!/usr/bin/env bash

set -euo pipefail

BRANCH=master
DEV=false
DOCKER_REGISTRY="https://registry-1.docker.io"
UTILS_TAG="20.08.11"


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
        "--dev")
            DEV=true
            shift
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
    curl -sf -H "Authorization: Bearer $TOKEN" "$DOCKER_REGISTRY/v2/$NAME/manifests/$TAG"
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

function get_image_without_branch() {
    echo "$1" | sed -E 's/__.*//g'
}

function get_pull_image() {
    if ! docker image inspect "$1" >/dev/null 2>&1; then
        echo "$2"
    fi
}

function get_branch_image() {
    if [[ $BRANCH == "master" ]]; then
        echo "$1"
    else
        echo "${1}__${BRANCH//\//-}"
    fi
}

function get_image_status() {
    # possible return values: up-to-date, outdated, newer, missing
    local LOCAL CLOUD
    local L_SHA256 C_SHA256
    local L_CREATED C_CREATED
    local M_IMG # master branch image (name)
    local B_IMG # branch image
    local P_IMG # pulling image
    local U_IMG # use image

    B_IMG=$(get_branch_image "$1")

    P_IMG=$B_IMG

    CLOUD=$(get_cloud_image "$B_IMG")

    if [[ -z $CLOUD ]]; then
        if [[ $B_IMG =~ __ ]]; then
            M_IMG=$(get_image_without_branch "$B_IMG")
            CLOUD=$(get_cloud_image "$M_IMG")
            if [[ -z $CLOUD ]]; then
                echo >&2 "❌ Image not found in $DOCKER_REGISTRY: $B_IMG, $M_IMG"
                exit 1
            else
                P_IMG=$M_IMG
            fi
        else
            echo >&2 "❌ Image not found in $DOCKER_REGISTRY: $B_IMG"
            exit 1
        fi
    fi

    C_SHA256=$(echo "$CLOUD" | sed -n '1p')
    U_IMG=$P_IMG
    P_IMG=$(get_pull_image "$C_SHA256" "$P_IMG")

    LOCAL=$(get_local_image "$B_IMG")
    if [[ -z $LOCAL ]]; then
        echo "missing $B_IMG $U_IMG $P_IMG"
        return
    fi

    L_SHA256=$(echo "$LOCAL" | sed -n '1p')

    if [[ $L_SHA256 == "$C_SHA256" ]]; then
        echo "up-to-date $B_IMG $U_IMG $P_IMG"
        return
    fi

    echo "outdated $B_IMG $U_IMG $P_IMG"
}

function pull_image() {
    echo "Pulling image $1"
    if ! docker pull "$1" >/dev/null 2>&1; then
        echo >&2 "Failed to pull image $1"
        exit 1
    fi
}

function ensure_utils_image() {
    echo "🌍 Checking for updates..."

    local STATUS
    local B_IMG # branch image
    local P_IMG # pulling image
    local U_IMG # use image
    local I_IMG # initial image

    if [[ $DEV == "true" ]]; then
        UTILS_IMG="exchangeunion/utils:latest"
        return
    fi

    if [[ $NETWORK == "mainnet" && $BRANCH == "master" ]]; then
        I_IMG="exchangeunion/utils:$UTILS_TAG"
    else
        I_IMG="exchangeunion/utils:latest"
    fi

    read -r STATUS B_IMG U_IMG P_IMG <<<"$(get_image_status "$I_IMG")"
    if [[ -z $U_IMG ]]; then
        exit 1
    fi

    case $STATUS in
        missing|outdated)
            while true; do
                read -p "Would you like to upgrade? (Warning: this may restart your environment and cancel all open orders) [Y/n]" yn
                case $yn in
                    [Yy]* )
                        if [[ -n $P_IMG ]]; then
                            UPGRADE=yes
                            pull_image "$P_IMG"
                            if [[ $BRANCH != "master" && ! $P_IMG =~ __ ]]; then
                                echo "Warning: Branch image $B_IMG not found. Fallback to $P_IMG"
                            fi
                        fi
                        ;;
                    [Nn]* )
                        break
                        ;;
                esac
            done
            ;;
    esac

    UTILS_IMG=$U_IMG
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

function get_utils_name() {
    local N
    N=$(docker ps -a --filter name="${NETWORK}_utils_" --format '{{.Names}}' | sed "s/${NETWORK}_utils_//" | sort -nr | head -n1)
    ((N++))
    echo "${NETWORK}_utils_${N}"
}

################################################################################
# MAIN
################################################################################

LOG_TIMESTAMP="$(date +%F-%H-%M-%S)"

parse_branch "$@"

choose_network

echo "🚀 Launching $NETWORK environment"

UPGRADE=no
ensure_utils_image
echo "Use $UTILS_IMG"

docker run --rm -it \
--name "$(get_utils_name)" \
-v /var/run/docker.sock:/var/run/docker.sock \
-v /:/mnt/hostfs \
-e HOST_PWD="$PWD" \
-e HOST_HOME="$HOME" \
-e NETWORK="$NETWORK" \
-e LOG_TIMESTAMP="$LOG_TIMESTAMP" \
-e UPGRADE=$UPGRADE \
"$UTILS_IMG" "$@"
