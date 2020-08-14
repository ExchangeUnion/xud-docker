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

function get_branch_image() {
    # replace character '/' with '-'
    echo "${1}__${BRANCH//\//-}"
}

function get_local_image_digest() {
    docker image inspect -f '{{.Config.Image}}' "$1" 2>/dev/null || true
}

function get_registry_image_digest() {
    local REPO TAG URL RESP
    REPO=$(echo "$1" | cut -d':' -f1)
    TAG=$(echo "$1" | cut -d':' -f2)
    TOKEN=$(get_token "$REPO")
    URL="$DOCKER_REGISTRY/v2/$REPO/manifests/$TAG"
    RESP=$(curl -sf "$URL" -H "Authorization: Bearer $TOKEN")
    if [[ -z $RESP ]]; then
        exit 0
    fi
    RESP=$(echo "$RESP" | grep v1Compatibility | head -1 | sed 's/^.*v1Compatibility":/printf/g' || echo "")
    if [[ -z $RESP ]]; then
        exit 0
    fi
    RESP=$(eval "$RESP")
    echo "$RESP" | sed -E 's/.*(sha256:[a-z0-9]+).*/\1/g'
}

function get_pull_image() {
    # possible return values: up-to-date, outdated, missing
    local IMG=$1
    local L_DIGEST R_DIGEST
    local B_IMG # branch image

    L_DIGEST=$(get_local_image_digest "$IMG")

    if [[ $BRANCH != "master" ]]; then
        B_IMG=$(get_branch_image "$IMG")
        R_DIGEST=$(get_registry_image_digest "$B_IMG")
        P_IMG=$B_IMG
    fi

    if [[ -z $R_DIGEST ]]; then
        R_DIGEST=$(get_registry_image_digest "$IMG")
        P_IMG=$IMG
    fi

    if [[ -z $L_DIGEST ]]; then
        if [[ -z $R_DIGEST ]]; then
            echo >&2 "Image not found: $IMG"
            exit 1
        fi
    else
        if [[ -z $R_DIGEST ]]; then
            echo "Warning: Use local $IMG (no such image in the registry)"
        else
            if [[ $L_DIGEST == "$R_DIGEST" ]]; then
                # image is up-to-date
                P_IMG=""
            fi
        fi
    fi
}

function pull_image() {
    echo "💿 Pulling image $1..."
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

    if [[ $DEV == "true" ]]; then
        UTILS_IMG="exchangeunion/utils:latest"
        return
    fi

    if [[ $NETWORK == "mainnet" && $BRANCH == "master" ]]; then
        UTILS_IMG="exchangeunion/utils:$UTILS_TAG"
    else
        UTILS_IMG="exchangeunion/utils:latest"
    fi

    get_pull_image "$UTILS_IMG"

    if [[ -n $P_IMG ]]; then
        if installed; then
            yes_or_no "$UPGRADE_PROMPT"
        else
            REPLY="yes"
        fi
        if [[ $REPLY == "yes" ]]; then
            UPGRADE="yes"
            pull_image "$P_IMG"
            docker tag "$P_IMG" "$UTILS_IMG"
        fi
    fi
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
