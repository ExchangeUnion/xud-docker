#!/usr/bin/env bash

set -euo pipefail

BRANCH=master
DEV=false
DOCKER_REGISTRY="https://registry-1.docker.io"
UTILS_TAG="20.12.07"


function print_help() {
    cat <<EOF
xud.sh 20.12.07
The launcher script for Exchange Union environment

USAGE:
    xud.sh [OPTIONS]

OPTIONS:
    -h, --help                                  Show this help
    -b, --branch <string>                       Git branch name
    --disable-update                            Skip update checks and enter xud-ctl shell directly
    --simnet-dir <path>                         Simnet environment directory path
    --testnet-dir <path>                        Testnet environment directory path
    --mainnet-dir <path>                        Mainnet environment directory path
    --external-ip <ip>                          Host machine Internet IP address
    --dev                                       Use local built utils image
    --use-local-images <image>[,<image>]        Use other built images

Bitcoind options:
    --bitcoind.mode [light|neutrino|external|native]
                                                Bitcoind service mode (default: light)
    --bitcoind.rpc-host <string>                External bitcoind RPC hostname
    --bitcoind.rpc-port <int>                   External bitcoind RPC port
    --bitcoind.rpc-user <string>                External bitcoind RPC username
    --bitcoind.rpc-password <string>            External bitcoind RPC password
    --bitcoind.zmqpubrawblock <address>         External bitcoind ZeroMQ raw blocks publication address
    --bitcoind.zmqpubrawtx <address>            External bitcoind ZeroMQ raw transactions publication address
    --bitcoind.expose-ports <port>[,<port>]     Expose bitcoind service ports to your host machine

Litecoind options:
    --litecoind.mode [light|neutrino|external|native]
                                                Litecoind service mode (default: light)
    --litecoind.rpc-host <string>               External litecoind RPC hostname
    --litecoind.rpc-port <int>                  External litecoind RPC port
    --litecoind.rpc-user <string>               External litecoind RPC username
    --litecoind.rpc-password <string>           External litecoind RPC password
    --litecoind.zmqpubrawblock <address>        External litecoind ZeroMQ raw blocks publication address
    --litecoind.zmqpubrawtx <address>           External litecoind ZeroMQ raw transactions publication address
    --litecoind.expose-ports <port>[,<port>]    Expose litecoind service ports to your host machine

Geth options:
    --geth.mode [light|infura|external|native]  Geth service mode (default: light)
    --geth.rpc-host <string>                    External geth RPC hostname
    --geth.rpc-port <int>                       External geth RPC port
    --geth.infura-project-id <string>           Infura geth provider project ID
    --geth.infura-project-secret <string>       Infura geth provider project secret
    --geth.expose-ports <port>[,<port>]         Expose geth service ports to your host machine
    --geth.cache <int>                          Geth cache size

Lndbtc options:
    --lndbtc.expose-ports <port>[,<port>]       Expose lndbtc service ports to your host machine
    --lndbtc.preserve-config                    Preserve lndbtc lnd.conf file during updates

Lndbtc options:
    --lndltc.expose-ports <port>[,<port>]       Expose lndltc service ports to your host machine
    --lndltc.preserve-config                    Preserve lndltc lnd.conf file during updates

Connext options:
    --connext.expose-ports <port>[,<port>]      Expose connext service ports to your host machine

Xud options:
    --xud.expose-ports <port>[,<port>]          Expose xud service ports to your host machine
    --xud.preserve-config                       Preserve xud xud.conf file during updates

Arby options:
    --arby.test-mode [true|false]               Production/Demo mode (default: true for simnet and testnet; false for mainnet)
    --arby.base-asset <string>                  Base asset symbol
    --arby.quote-asset <string>                 Quote asset symbol
    --arby.cex-base-asset <string>              Centralized exchange base asset symbol
    --arby.cex-quote-asset <string>             Centralized exchange quote asset symbol
    --arby.test-centralized-baseasset-balance   CEX base asset balance for demo mode
    --arby.test-centralized-quoteasset-balance  CEX quote asset balance for demo mode
    --arby.cex <string>                         CEX (binance/kraken)
    --arby.cex-api-key <string>                 CEX API key
    --arby.cex-api-secret <string>              CEX API secret
    --arby.margin <double>                      Trade margin
    --arby.disabled [true|false]                Enable/Disable arby service

Boltz options:
    --boltz.disabled [true|false]               Enable/Disable boltz service

Webui options:
    --webui.disabled [true|false]               Enable/Disable webui service
    --webui.expose-ports <port>[,<port>]        Expose webui service ports to your host machine

Proxy options:
    --proxy.disabled [true|false]               Enable/Disable proxy service
    --proxy.expose-ports <port>[,<port>]        Expose proxy service ports to your host machine
EOF
}


function parse_opts() {
    local OPTION VALUE
    while [[ $# -gt 0 ]]; do
        case $1 in
        "-h" | "--help" )
            print_help
            exit 1
            ;;
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
            break
            ;;
        2 | testnet)
            NETWORK=testnet
            break
            ;;
        3 | mainnet)
            NETWORK=mainnet
            break
            ;;
        *)
            continue
            ;;
        esac
        shopt -u nocasematch
    done
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
        echo >&2 "❌ Failed to pull image $1. This may be a Docker issue or a permissions issue. Check your Docker installation and make sure you have added your user to the docker group: https://docs.docker.com/engine/install/linux-postinstall/"
        exit 1
    fi
}

function ensure_utils_image() {
    local STATUS
    local B_IMG # branch image
    local P_IMG # pulling image
    local U_IMG # use image
    local I_IMG # initial image

    if [[ $DEV == "true" ]]; then
        UTILS_IMG=$(get_branch_image "exchangeunion/utils:latest")
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
            if [[ -n $P_IMG ]]; then
                pull_image "$P_IMG"
                if [[ $BRANCH != "master" && ! $P_IMG =~ __ ]]; then
                    echo "Warning: Branch image $B_IMG not found. Fallback to $P_IMG"
                fi
            fi
            ;;
        newer)
            echo "Warning: Use local $B_IMG (newer than cloud $P_IMG)"
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

parse_opts "$@"

choose_network

ensure_utils_image

echo "🚀 Launching $NETWORK environment"

docker run --rm -it \
--name "$(get_utils_name)" \
-v /var/run/docker.sock:/var/run/docker.sock \
-v /:/mnt/hostfs \
-e HOST_PWD="$PWD" \
-e HOST_HOME="$HOME" \
-e NETWORK="$NETWORK" \
-e LOG_TIMESTAMP="$LOG_TIMESTAMP" \
--entrypoint python \
"$UTILS_IMG" \
-m launcher "$@"
