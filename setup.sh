#!/usr/bin/env bash

set -euo pipefail


################################################################################
# Global Variables                                                             #
################################################################################
BRANCH="master"
DEV="false"
DOCKER_REGISTRY="https://registry-1.docker.io"
UTILS_TAG="20.08.11"
UPGRADE="no"
UPGRADE_PROMPT="Would you like to upgrade? (Warning: this may restart your environment and cancel all open orders)"
HOME_DIR="$HOME/.xud-docker"
SIMNET_DIR=""
TESTNET_DIR=""
MAINNET_DIR=""
NETWORK_DIR=""
LOGS_DIR=""
DATA_DIR=""


################################################################################
# Utility Functions                                                            #
################################################################################
function normalize_reply() {
    # convert to lowercase and trim whitespaces
    echo "$1" | tr '[:upper:]' '[:lower:]' | awk '{$1=$1;print}'
}

function yes_or_no() {
    local PROMPT=$1
    local DEFAULT=${2:-yes}
    while true; do
        if [[ $DEFAULT == "yes" ]]; then
            read -r -p "$PROMPT [Y/n] "
        else
            read -r -p "$PROMPT [y/N] "
        fi
        REPLY=$(normalize_reply "$REPLY")
        case $REPLY in
            y|yes) REPLY="yes"; break;;
            n|no) REPLY="no"; break;;
            '') echo REPLY="$DEFAULT"; break;;
        esac
    done
}

function ensure_directory() {
    local DIR=$1

    if [[ ! -e $DIR ]]; then
        mkdir -p "$DIR"
    fi

    if [[ ! -d $DIR ]]; then
        echo >&2 "$DIR is not a directory"
        exit 1
    fi

    if [[ ! -r $DIR ]]; then
        echo >&2 "$DIR is not readable"
        exit 1
    fi

    if [[ ! -w $DIR ]]; then
        sudo chown "$USER":"$USER" "$DIR"
    fi
}


################################################################################
# Docker Related Functions                                                     #
################################################################################
function get_token() {
    local REPO=$1
    local URL="https://auth.docker.io/token?service=registry.docker.io&scope=repository:$REPO:pull"
    curl -sf "$URL" | sed -E 's/^.*"token":"([^,]*)",.*$/\1/g'
}

function get_image_metadata() {
    local TOKEN NAME TAG
    NAME=$(echo "$1" | cut -d':' -f1)
    TAG=$(echo "$1" | cut -d':' -f2)
    TOKEN=$(get_token "$NAME")
    local URL="$DOCKER_REGISTRY/v2/$NAME/manifests/$TAG"
    curl -sf "$URL" -H "Authorization: Bearer $TOKEN"
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
        # replace character '/' with '-'
        echo "${1}__${BRANCH//\//-}"
    fi
}

function get_image_status() {
    # possible return values: up-to-date, outdated, missing
    local LOCAL CLOUD
    local L_SHA256 C_SHA256
    local M_IMG # master branch image (name)
    local B_IMG # branch image
    local P_IMG # pulling image
    local U_IMG=$1 # use image

    B_IMG=$(get_branch_image "$1")

    P_IMG=$B_IMG

    CLOUD=$(get_cloud_image "$B_IMG")

    if [[ -z $CLOUD ]]; then
        if [[ $B_IMG =~ __ ]]; then
            M_IMG=$(get_image_without_branch "$B_IMG")
            CLOUD=$(get_cloud_image "$M_IMG")
            if [[ -z $CLOUD ]]; then
                echo >&2 "Image $B_IMG and $M_IMG not found in registry"
                exit 1
            else
                P_IMG=$M_IMG
            fi
        else
            echo >&2 "Image $B_IMG not found in registry"
            exit 1
        fi
    fi

    C_SHA256=$(echo "$CLOUD" | sed -n '1p')
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

function get_utils_name() {
    local N
    N=$(docker ps -a --filter name="${NETWORK}_utils_" --format '{{.Names}}' | sed "s/${NETWORK}_utils_//" | sort -nr | head -n1)
    ((N++))
    echo "${NETWORK}_utils_${N}"
}


################################################################################
# Business Logic Functions                                                     #
################################################################################
function read_string_key() {
    local KEY=$1
    local FILE=$2
    local LINE
    LINE=$(grep -q "$KEY" "$FILE")
    if [[ -n $LINE ]]; then
        echo "$LINE" | cut -d '=' -f 2
    fi
}

function parse_conf() {
    local GENERAL_CONF="$HOME_DIR/xud-docker.conf"
    if [[ -e $GENERAL_CONF ]]; then
        SIMNET_DIR=$(read_string_key "simnet-dir" "$GENERAL_CONF")
        TESTNET_DIR=$(read_string_key "testnet-dir" "$GENERAL_CONF")
        MAINNET_DIR=$(read_string_key "mainnet-dir" "$GENERAL_CONF")
    fi
}

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
                    echo >&2 "Missing option value: $OPTION"
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
        "--simnet-dir")
            if [[ $1 =~ = ]]; then
                VALUE=$(echo "$1" | cut -d'=' -f2)
            else
                OPTION=$1
                shift
                if [[ $# -eq 0 || $1 =~ ^- ]]; then
                    echo >&2 "Missing option value: $OPTION"
                    exit 1
                fi
            fi
            SIMNET_DIR=$VALUE
            ;;
        "--testnet-dir")
            if [[ $1 =~ = ]]; then
                VALUE=$(echo "$1" | cut -d'=' -f2)
            else
                OPTION=$1
                shift
                if [[ $# -eq 0 || $1 =~ ^- ]]; then
                    echo >&2 "Missing option value: $OPTION"
                    exit 1
                fi
            fi
            TESTNET_DIR=$VALUE
            ;;
        "--mainnet-dir")
            if [[ $1 =~ = ]]; then
                VALUE=$(echo "$1" | cut -d'=' -f2)
            else
                OPTION=$1
                shift
                if [[ $# -eq 0 || $1 =~ ^- ]]; then
                    echo >&2 "Missing option value: $OPTION"
                    exit 1
                fi
            fi
            MAINNET_DIR=$VALUE
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
        read -r -p "Please choose the network: "
        REPLY=$(normalize_reply "$REPLY")
        case $REPLY in
            1|simnet)
                NETWORK="simnet"
                NETWORK_DIR="$SIMNET_DIR"
                break;;
            2|testnet)
                NETWORK="testnet"
                NETWORK_DIR="$TESTNET_DIR"
                break;;
            3|mainnet)
                NETWORK="mainnet"
                NETWORK_DIR="$MAINNET_DIR"
                break;;
        esac
    done
}

function installed() {
    local DATA_FILES CONTAINERS
    DATA_FILES=$(ls -A "$DATA_DIR")
    CONTAINERS=$(docker ps -aq -f "name=${NETWORK}_")
    if [[ -z $DATA_FILES && -z $CONTAINERS ]]; then
        return 0
    else
        return 1
    fi
}

function check_for_updates() {
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
    UTILS_IMG=$U_IMG

    case $STATUS in
        missing|outdated)
            if installed; then
                REPLY="yes"
            else
                yes_or_no "$UPGRADE_PROMPT"
            fi
            if [[ $REPLY == "yes" ]]; then
                UPGRADE="yes"
                pull_image "$P_IMG"
                docker tag "$P_IMG" "$U_IMG"
            fi
            ;;
    esac
}


################################################################################
# Main Business Logic                                                          #
################################################################################
ensure_directory "$HOME_DIR"
parse_conf
parse_args "$@"
if [[ -z $SIMNET_DIR ]]; then
    SIMNET_DIR="$HOME_DIR/simnet"
fi
if [[ -z $TESTNET_DIR ]]; then
    TESTNET_DIR="$HOME_DIR/testnet"
fi
if [[ -z $MAINNET_DIR ]]; then
    MAINNET_DIR="$HOME_DIR/mainnet"
fi
choose_network
ensure_directory "$NETWORK_DIR"
NETWORK_DIR=$(realpath "$NETWORK_DIR")
LOGS_DIR="$NETWORK_DIR/logs"
ensure_directory "$LOGS_DIR"
DATA_DIR="$NETWORK_DIR/data"
ensure_directory "$DATA_DIR"

echo "🚀 Launching $NETWORK environment"
check_for_updates
docker run --rm -it \
--name "$(get_utils_name)" \
-v /var/run/docker.sock:/var/run/docker.sock \
-v /:/mnt/hostfs \
-e HOST_PWD="$PWD" \
-e HOST_HOME="$HOME" \
-e NETWORK="$NETWORK" \
-e UPGRADE="$UPGRADE" \
"$UTILS_IMG" "$@"
