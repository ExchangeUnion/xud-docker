#!/usr/bin/env bash

set -euo pipefail

BRANCH=master
DEV=false

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

DOCKER_REGISTRY="https://registry-1.docker.io"

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

function get_image_status() {
    # possible return values: up-to-date, outdated, newer, missing
    local LOCAL CLOUD
    local L_SHA256 C_SHA256
    local L_CREATED C_CREATED
    local M_IMG # master branch image (name)
    local B_IMG # branch image
    local P_IMG # pulling image
    local U_IMG # use image

    if [[ $BRANCH == "master" ]]; then
        B_IMG="$1"
    else
        B_IMG="${1}__${BRANCH//\//-}"
    fi

    P_IMG=$B_IMG

    CLOUD=$(get_cloud_image "$B_IMG")
    echo -e "get_cloud_image $B_IMG\n$CLOUD" >> "$LOGFILE"

    if [[ -z $CLOUD ]]; then
        if [[ $B_IMG =~ __ ]]; then
            M_IMG=$(get_image_without_branch "$B_IMG")
            CLOUD=$(get_cloud_image "$M_IMG")
            echo -e "get_cloud_image $M_IMG\n$CLOUD" >> "$LOGFILE"
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

    echo -e "get_local_image $B_IMG\n$LOCAL" >> "$LOGFILE"

    L_SHA256=$(echo "$LOCAL" | sed -n '1p')

    if [[ $L_SHA256 == "$C_SHA256" ]]; then
        echo "up-to-date $B_IMG $U_IMG $P_IMG"
        return
    fi

    L_CREATED=$(echo "$LOCAL" | sed -n '2p')
    C_CREATED=$(echo "$CLOUD" | sed -n '2p')

    if [[ $L_CREATED > $C_CREATED ]]; then
        echo "newer $B_IMG $U_IMG $P_IMG"
    else
        echo "outdated $B_IMG $U_IMG $P_IMG"
    fi
}

function pull_image() {
    echo "Pulling image $1"
    if ! docker pull "$1" >/dev/null 2>&1; then
        echo >&2 "❌ Failed to pull image $1"
        exit 1
    fi
}

function ensure_utils_image() {
    local STATUS
    local B_IMG # branch image
    local P_IMG # pulling image
    local U_IMG # use image

    if [[ $DEV == "true" ]]; then
        UTILS_IMG="exchangeunion/utils:latest"
        return
    fi

    read -r STATUS B_IMG U_IMG P_IMG <<<"$(get_image_status "exchangeunion/utils:latest")"
    if [[ -z $U_IMG ]]; then
        exit 1
    fi
    echo "STATUS=$STATUS" >> "$LOGFILE"
    echo "B_IMG=$B_IMG" >> "$LOGFILE"
    echo "U_IMG=$U_IMG" >> "$LOGFILE"
    echo "P_IMG=$P_IMG" >> "$LOGFILE"

    case $STATUS in
        missing|outdated)
            if [[ -n $P_IMG ]]; then
                pull_image "$P_IMG"
                if [[ $BRANCH != "master" && ! $P_IMG =~ __ ]]; then
                    echo "Warning: Branch image $B_IMG not found. Fallback to $P_IMG"
                fi
            fi
            ;;
        newer)
            echo "Warning: Use local $B_IMG (newer than $P_IMG)"
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

################################################################################
# MAIN
################################################################################

HOME_DIR="$HOME/.xud-docker"

if [[ ! -e $HOME_DIR ]]; then
    mkdir "$HOME_DIR"
fi

ensure_directory "$HOME_DIR"

LOG_TIMESTAMP="$(date +%F-%H-%M-%S)"
LOGFILE="$HOME_DIR/xud-docker-$LOG_TIMESTAMP.log"
touch "$LOGFILE"

echo "--------------------------------------------------------------------------------" >> "$LOGFILE"
echo ":: XUD-DOCKER ::" >> "$LOGFILE"
echo "--------------------------------------------------------------------------------" >> "$LOGFILE"

date >> "$LOGFILE"
echo "" >> "$LOGFILE"

uname -a >> "$LOGFILE"
echo "" >> "$LOGFILE"

bash --version >> "$LOGFILE"
echo "" >> "$LOGFILE"

docker version >> "$LOGFILE"
echo "" >> "$LOGFILE"

echo "$*" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# shellcheck disable=SC2068
parse_branch $@

ensure_utils_image

# shellcheck disable=SC2068
# shellcheck disable=SC2086
docker run --rm \
-e PROG="$0" \
--entrypoint args_parser \
"$UTILS_IMG" \
$@

choose_network

echo "🚀 Launching $NETWORK environment"

HOME_DIR=$HOME/.xud-docker

if [[ ! -e $HOME_DIR ]]; then
    mkdir "$HOME_DIR"
fi

# shellcheck disable=SC2068
# shellcheck disable=SC2086
# NETWORK_DIR will be evaluated after running the command below
VARS="$(docker run --rm \
-v /var/run/docker.sock:/var/run/docker.sock \
-v "$HOME_DIR":/root/.xud-docker \
-v /:/mnt/hostfs \
-e HOME_DIR="$HOME_DIR" \
-e NETWORK="$NETWORK" \
--entrypoint config_parser \
"$UTILS_IMG" \
$@)"

eval "$VARS"

NETWORK_DIR=$(realpath "$NETWORK_DIR")

ensure_directory "$NETWORK_DIR"

# TODO properly handle network logfile permission problem
# cat "$LOGFILE" > "$NETWORK_DIR/${NETWORK}.log"

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
-e LOG_TIMESTAMP="$LOG_TIMESTAMP" \
--entrypoint python \
"$UTILS_IMG" \
-m launcher $@
