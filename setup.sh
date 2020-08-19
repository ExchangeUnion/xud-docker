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
HOME_DIR="$HOME/.xud-docker"
SIMNET_DIR=""
TESTNET_DIR=""
MAINNET_DIR=""
NETWORK_DIR=""
LOGS_DIR=""
DATA_DIR=""
LAUNCH_ID=$(date +%s)
GENERAL_CONF="$HOME_DIR/xud-docker.conf"
GENERAL_CONF_SAMPLE="$HOME_DIR/sample-xud-docker.conf"

case $(uname -m) in
    x86_64)
        ARCH="amd64"
        ;;
    aarch64)
        ARCH="arm64"
        ;;
esac


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
            '') REPLY="$DEFAULT"; break;;
        esac
    done
}

function ensure_directory() {
    local DIR=$1

    if [[ ! -e $DIR ]]; then
        mkdir -p "$DIR"
    fi

    if [[ ! -d $DIR ]]; then
        echo >&2 "Error: $DIR is not a directory"
        exit 1
    fi

    if [[ ! -r $DIR ]]; then
        echo >&2 "Error: $DIR is not readable"
        exit 1
    fi

    if [[ ! -w $DIR ]]; then
        sudo chown "$USER:$USER" "$DIR"
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
    if [[ $BRANCH == "master" ]]; then
        echo "$1"
    fi
    # replace character '/' with '-'
    echo "${1}__${BRANCH//\//-}"
}

function get_local_image_id() {
    docker image inspect -f '{{.Id}}' "$1" 2>/dev/null || true
}

function get_manifest() {
    local REPO=$1
    local REF=$2
    local URL
    URL="$DOCKER_REGISTRY/v2/$REPO/manifests/$REF"
    curl -sf "$URL" \
-H "Authorization: Bearer $TOKEN" \
-H "Accept: application/vnd.docker.distribution.manifest.list.v2+json,Accept: application/vnd.docker.distribution.manifest.v2+json"
}

function get_manifest_current() {
    local REPO=$1
    local TAG=$1
    local MANIFEST DIGEST
    MANIFEST=$(get_manifest "$REPO" "$TAG")
    DIGEST=$(echo "$MANIFEST" | grep -B 2 "$ARCH" | grep "digest" | sed -E "s/^.*: \"(.*)\".*$/\1/")
    get_manifest "$REPO" "$DIGEST"
}

function get_registry_image_id() {
    IFS=':' read -r REPO TAG <<< "$1"
    TOKEN=$(get_token "$REPO")
    local MANIFEST
    MANIFEST=$(get_manifest_current "$REPO" "$TAG")
    unset TOKEN
    echo "$MANIFEST" | grep -A 3 "config" | grep "digest" | sed -E "s/^.*: \"(.*)\".*$/\1/"
}

function get_pull_image() {
    # possible return values: up-to-date, outdated, missing
    local IMG=$1
    local L_ID R_ID
    local B_IMG # branch image

    R_ID=""

    if [[ $BRANCH != "master" ]]; then
        B_IMG=$(get_branch_image "$IMG")
        R_ID=$(get_registry_image_id "$B_IMG")
        P_IMG=$B_IMG
    fi

    if [[ -z $R_ID ]]; then
        R_ID=$(get_registry_image_id "$IMG")
        P_IMG=$IMG
    fi

    UTILS_IMG=$P_IMG

    L_ID=$(get_local_image_id "$P_IMG")

    if [[ -z $L_ID ]]; then
        if [[ -z $R_ID ]]; then
            echo >&2 "Error: Image not found: $IMG"
            exit 1
        fi
    else
        if [[ -z $R_ID ]]; then
            echo "Warning: Use local $IMG (no such image in the registry)"
        else
            if [[ $L_ID == "$R_ID" ]]; then
                # image is up-to-date
                P_IMG=""
            fi
        fi
    fi
}

function pull_image() {
    echo "💿 Pulling image $1..."
    if ! docker pull "$1"; then
        echo >&2 "Error: Failed to pull image $1"
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
    # remove comments | remove empty lines | remove leading & trailing whitespaces | grep key | select the last one
    LINE=$(cat "$FILE" | sed -E 's/#.*$//' | sed -E '/^\s*$/d' | sed -E 's/^\s*(.*)\s*$/\1/' | grep "$KEY" | tail -n1)
    if [[ -n $LINE && $LINE =~ ^# ]]; then
        # split line by '=' | trim extra characters around string value
        echo "$LINE" | cut -d '=' -f 2 | sed -E 's/^.*"(.*)".*$/\1/'
    fi
}

function write_general_conf_sample() {
    cat <<'EOF' >"$GENERAL_CONF_SAMPLE"
#simnet-dir = "$home_dir/simnet"
#testnet-dir = "$home_dir/testnet"
#mainnet-dir = "$home_dir/mainnet"
EOF
}

function write_network_conf_sample() {
    case $NETWORK in
        simnet)
            cat <<'EOF' >"$NETWORK_CONF_SAMPLE"
# Sample configuration file for xud-docker simnet environment
#
# You can copy this file to your simnet directory and name it simnet.conf to
# customize your simnet environment.
#
# The `expose-ports` option value is an array of strings. The element syntax
# follows Docker published port style (https://docs.docker.com/config/containers
# /container-networking/#published-ports). There are three basic formats:
# 1. <container_port> (e.g. "8080")
# 2. <host_port>:<container_port> (e.g. "80:8080")
# 3. <host_ip>:<host_port>:<container_port> (e.g. "127.0.0.1:80:8080")
#

[lndbtc]
# 29735 - P2P port
# 30009 - gRPC port
# 30010 - REST port
#expose-ports = ["29735", "30009:10009", "30010:10010"]

[lndltc]
# 30735 - P2P port
# 31009 - gRPC port
# 31010 - REST port
#expose-ports = ["30735", "31009:10009", "31010:10010"]

[connext]
# 25040 - connext API port
#expose-ports = ["25040:5040"]

[xud]
# 28885 - P2P port
# 28886 - gRPC port
# 28080 - webproxy port
#expose-ports = ["28885", "28886", "28080:8080"]

[arby]
#live-cex="false"
#base-asset = "ETH"
#quote-asset = "BTC"
#test-centralized-baseasset-balance = "123"
#test-centralized-quoteasset-balance = "321"
#binance-api-key = "your api key"
#binance-api-secret = "your api secret"
#margin = "0.04"
#disabled = false

[webui]
#disabled = false
#expose-ports = ["28888:8080"]
EOF
            ;;
        testnet)
            cat <<'EOF' >"$NETWORK_CONF_SAMPLE"
# Sample configuration file for xud-docker testnet environment
#
# You can copy this file to your testnet directory and name it testnet.conf to
# customize your testnet environment.
#
# The `expose-ports` option value is an array of strings. The element syntax
# follows Docker published port style (https://docs.docker.com/config/containers
# /container-networking/#published-ports). There are three basic formats:
# 1. <container_port> (e.g. "8080")
# 2. <host_port>:<container_port> (e.g. "80:8080")
# 3. <host_ip>:<host_port>:<container_port> (e.g. "127.0.0.1:80:8080")
#


# The path to the directory to store your backup in. This should be located on
# an external drive, which usually is mounted in /mnt or /media.
#backup-dir = "/your/backup/path"

[bitcoind]
# This option specifies the container's volume mapping data directory. It
# will be ignored if you set mode as "external", "neutrino" or "light".
#dir = "$testnet_dir/data/bitcoind"

# 18332 - JSON-RPC port
# 18333 - P2P port
# 38332 - ZeroMQ raw blocks publication port (zmqpubrawblock)
# 38333 - ZeroMQ raw transactions publication port (zmqpubrawtx)
#expose-ports = ["18332", "18333", "38332:28332", "38333:28333"]

# This option specifies the mode of the bitcoind node. The available values are
# "native", "external", "neutrino" and "light". The default value is "light" and
# is the same as "neutrino" at the moment. Set value to "external" and fill
# options below to enable using external bitcoind node. Setting value to
# "neutrino" will use lnd's internal light client and ignore mode "external"
# related options.
#mode = "light"
#rpc-host = "127.0.0.1"
#rpc-port = 18332
#rpc-user = "xu"
#rpc-password = "xu"
#zmqpubrawblock = "tcp://127.0.0.1:38332"
#zmqpubrawtx = "tcp://127.0.0.1:38333"

[litecoind]
# This option specifies the container's volume mapping data directory. It
# will be ignored if you set mode as "external", "neutrino" or "light".
#dir = "$testnet_dir/data/litecoind"

# 19332 - JSON-RPC port
# 19333 - P2P port
# 39332 - ZeroMQ raw blocks publication port (zmqpubrawblock)
# 39333 - ZeroMQ raw transactions publication port (zmqpubrawtx)
#expose-ports = ["19332", "19333", "39332:28332", "39333:28333"]

# This option specifies the mode of the litecoind node. The available values are
# "native", "external", "neutrino" and "light". The default value is "light" and
# is the same as "neutrino" at the moment. Set value to "external" and fill
# options below to enable using external litecoind node. Setting value to
# "neutrino" will use lnd's internal light client and ignore mode "external"
# related options.
#mode = "light"
#rpc-host = "127.0.0.1"
#rpc-port = 19332
#rpc-user = "xu"
#rpc-password = "xu"
#zmqpubrawblock = "tcp://127.0.0.1:39332"
#zmqpubrawtx = "tcp://127.0.0.1:39333"

[geth]
# This option specifies the container's volume mapping data directory. Has
# to be located on a fast SSD.
#dir = "$testnet_dir/data/geth"

# This option specifies the container's volume mapping ancient chaindata
# directory. Can be located on a slower HDD.
#ancient-chaindata-dir = "$testnet_dir/data/geth/chaindata"

# 18545 - JSON-RPC port
# 40303/udp - P2P port
#expose-ports = ["18545:8545", "40303:30303/udp"]

# This option specifies the mode of the geth node. The available values are
# "native", "external", "infura" and "light". The default value is "light" and
# connects you to a random full-node. Set value to "external" and fill rpc-host
# with geth/eth-provider URL and rpc-port with the port to enable using external
# geth node.
#mode = "light"
#rpc-host = "127.0.0.1"
#rpc-port = 18545

# Setting `mode` option "infura" will let connext node use Infura as a Geth API
# provider and ignore mode "external" related options.
#infura-project-id = ""
#infura-project-secret = ""

# This option specifies the geth performance tuning option `--cache`. The
# default value in our setup is 256, which keeps RAM consumption ~4 GB, max
# value is 10240. The more, the faster the initial sync.
#cache = 256

[lndbtc]
# 19735 - P2P port
# 20009 - gRPC port
# 20010 - REST port
#expose-ports = ["19735", "20009:10009", "20010:10010"]

[lndltc]
# 20735 - P2P port
# 21009 - gRPC port
# 21010 - REST port
#expose-ports = ["20735", "21009:10009", "21010:10010"]

[connext]
# 15040 - connext API port
#expose-ports = ["15040:5040"]

[xud]
# 18885 - P2P port
# 18886 - gRPC port
# 18080 - webproxy port
#expose-ports = ["18885", "18886", "18080:8080"]

[arby]
#live-cex="false"
#base-asset = "ETH"
#quote-asset = "BTC"
#test-centralized-baseasset-balance = "123"
#test-centralized-quoteasset-balance = "321"
#binance-api-key = "your api key"
#binance-api-secret = "your api secret"
#margin = "0.04"
#disabled = false

[boltz]
#disabled = false

[webui]
#disabled = false
#expose-ports = ["18888:8080"]
EOF
            ;;
        mainnet)
            cat <<'EOF' >"$NETWORK_CONF_SAMPLE"
# Sample configuration file for xud-docker mainnet environment
#
# You can copy this file to your mainnet directory and name it mainnet.conf to
# customize your mainnet environment.
#
# The `expose-ports` option value is an array of strings. The element syntax
# follows Docker published port style (https://docs.docker.com/config/containers
# /container-networking/#published-ports). There are three basic formats:
# 1. <container_port> (e.g. "8080")
# 2. <host_port>:<container_port> (e.g. "80:8080")
# 3. <host_ip>:<host_port>:<container_port> (e.g. "127.0.0.1:80:8080")
#


# The path to the directory to store your backup in. This should be located on
# an external drive, which usually is mounted in /mnt or /media.
#backup-dir = "/your/backup/path"

[bitcoind]
# This option specifies the container's volume mapping data directory. It
# will be ignored if you set mode as "external", "neutrino" or "light".
#dir = "$mainnet_dir/data/bitcoind"

# 8332 - JSON-RPC port
# 8333 - P2P port
# 28332 - ZeroMQ raw blocks publication port (zmqpubrawblock)
# 28333 - ZeroMQ raw transactions publication port (zmqpubrawtx)
#expose-ports = ["8332", "8333", "28332", "28333"]

# This option specifies the mode of the bitcoind node. The available values are
# "native", "external", "neutrino" and "light". The default value is "light" and
# is the same as "neutrino" at the moment. Set value to "external" and fill
# options below to enable using external bitcoind node. Setting value to
# "neutrino" will use lnd's internal light client and ignore mode "external"
# related options.
#mode = "light"
#rpc-host = "127.0.0.1"
#rpc-port = 8332
#rpc-user = "xu"
#rpc-password = "xu"
#zmqpubrawblock = "tcp://127.0.0.1:28332"
#zmqpubrawtx = "tcp://127.0.0.1:28333"

[litecoind]
# This option specifies the container's volume mapping data directory. It
# will be ignored if you set mode as "external", "neutrino" or "light".
#dir = "$mainnet_dir/data/litecoind"

# 9332 - JSON-RPC port
# 9333 - P2P port
# 29332 - ZeroMQ raw blocks publication port (zmqpubrawblock)
# 29333 - ZeroMQ raw transactions publication port (zmqpubrawtx)
#expose-ports = ["9332", "9333", "29332:28332", "29333:28333"]

# This option specifies the mode of the litecoind node. The available values are
# "native", "external", "neutrino" and "light". The default value is "light" and
# is the same as "neutrino" at the moment. Set value to "external" and fill
# options below to enable using external litecoind node. Setting value to
# "neutrino" will use lnd's internal light client and ignore mode "external"
# related options.
#mode = "light"
#rpc-host = "127.0.0.1"
#rpc-port = 9332
#rpc-user = "xu"
#rpc-password = "xu"
#zmqpubrawblock = "tcp://127.0.0.1:29332"
#zmqpubrawtx = "tcp://127.0.0.1:29333"

[geth]
# This option specifies the container's volume mapping data directory. Has
# to be located on a fast SSD.
#dir = "$mainnet_dir/data/geth"

# This option specifies the container's volume mapping ancient chaindata
# directory. Can be located on a slower HDD.
#ancient-chaindata-dir = "$mainnet_dir/data/geth/chaindata"

# 8545 - JSON-RPC port
# 30303/udp - P2P port
#expose-ports = ["8545", "30303/udp"]

# This option specifies the mode of the geth node. The available values are
# "native", "external", "infura" and "light". The default value is "light" and
# connects you to a random full-node. Set value to "external" and fill rpc-host
# with geth/eth-provider URL and rpc-port with the port to enable using external
# geth node.
#mode = "light"
#rpc-host = "127.0.0.1"
#rpc-port = 8545

# Setting `mode` option "infura" will let connext node use Infura as a Geth API
# provider and ignore mode "external" related options.
#infura-project-id = ""
#infura-project-secret = ""

# This option specifies the geth performance tuning option `--cache`. The
# default value in our setup is 256, which keeps RAM consumption ~4 GB, max
# value is 10240. The more, the faster the initial sync.
#cache = 256

[lndbtc]
# 9735 - P2P port
# 10009 - gRPC port
# 10010 - REST port
#expose-ports = ["9735", "10009", "10010"]

[lndltc]
# 10735 - P2P port
# 11009 - gRPC port
# 11010 - REST port
#expose-ports = ["10735", "11009:10009", "11010:10010"]

[connext]
# 5040 - connext API port
#expose-ports = ["5040"]

[xud]
# 8885 - P2P port
# 8886 - gRPC port
# 8080 - webproxy port
#expose-ports = ["8885", "8886", "8080"]

[arby]
#live-cex="false"
#base-asset = "ETH"
#quote-asset = "BTC"
#test-centralized-baseasset-balance = "123"
#test-centralized-quoteasset-balance = "321"
#binance-api-key = "your api key"
#binance-api-secret = "your api secret"
#margin = "0.04"
#disabled = false

[webui]
#disabled = false
#expose-ports = ["8888:8080"]
EOF
            ;;
    esac
}

function parse_general_conf() {
    if ! write_general_conf_sample >/dev/null 2>&1; then
        sudo chown "$USER:$USER" "$GENERAL_CONF_SAMPLE"
        write_general_conf_sample
    fi

    if [[ -e $GENERAL_CONF ]]; then
        SIMNET_DIR=$(read_string_key "simnet-dir" "$GENERAL_CONF" || true)
        TESTNET_DIR=$(read_string_key "testnet-dir" "$GENERAL_CONF" || true)
        MAINNET_DIR=$(read_string_key "mainnet-dir" "$GENERAL_CONF" || true)
    fi
}

function parse_network_conf() {
    if ! write_network_conf_sample >/dev/null 2>&1; then
        sudo chown "$USER:$USER" "$NETWORK_CONF_SAMPLE"
        write_network_conf_sample
    fi

    if [[ -e $NETWORK_CONF ]]; then
        :
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
                    echo >&2 "Error: Missing option value: $OPTION"
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
                    echo >&2 "Error: Missing option value: $OPTION"
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
                    echo >&2 "Error: Missing option value: $OPTION"
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
                    echo >&2 "Error: Missing option value: $OPTION"
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
        return 1
    else
        return 0
    fi
}

function get_latest_snapshot() {
    local FILE
    FILE=$(ls -t1 "$SNAPSHOT_DIR" | head -n 1)
    if [[ -n $FILE ]]; then
        cat "$SNAPSHOT_DIR/$FILE"
    fi
}

function get_prev_utils() {
    local SNAPSHOT PREV_ID L_ID
    SNAPSHOT=$(get_latest_snapshot)
    if [[ -n $SNAPSHOT ]]; then
        IFS=',' read -r PREV_UTILS PREV_ID <<< "$(echo "$SNAPSHOT" | sed -En "s/^# It's generated by xud-docker (.*) \((.*)\)$/\1,\2/p")"
        L_ID=$(get_local_image_id "$PREV_UTILS")
        if [[ $L_ID != "$PREV_ID" ]]; then
            PREV_UTILS=""
        fi
    else
        PREV_UTILS=""
    fi
}

function check_for_updates() {
    echo "🌍 Checking for updates..."

    if [[ $DEV == "true" ]]; then
        UTILS_IMG=$(get_branch_image "exchangeunion/utils:latest")
        return
    fi

    if [[ $NETWORK == "mainnet" && $BRANCH == "master" ]]; then
        UTILS_IMG="exchangeunion/utils:$UTILS_TAG"
    else
        UTILS_IMG="exchangeunion/utils:latest"
    fi

    get_pull_image "$UTILS_IMG" # Will set P_IMG (pulling image name) if utils image is outdated
    get_prev_utils # Will set PREV_UTILS if there is a previous snapshot

    # If there is a new utils or utils branch changed then we need to ask the user
    if [[ -n $P_IMG || $UTILS_IMG != "$PREV_UTILS" ]]; then
        if installed; then
            # Print utils update details
            echo "There are some changes of utils image:"
            if [[ -n $P_IMG ]]; then
                echo "* New image available: $P_IMG"
            fi
            if [[ $UTILS_IMG != "$PREV_UTILS" ]]; then
                if [[ -n $PREV_UTILS ]]; then
                    P="n/a"
                else
                    P="$PREV_UTILS"
                fi
                echo "* Branch changed: $P -> $UTILS_IMG"
                unset P
            fi
            yes_or_no "Would you like to apply these changes? (Warning: this may restart your environment and cancel all open orders)"
        else
            # A pristine environment will always use a new utils
            REPLY="yes"
        fi
        if [[ $REPLY == "yes" ]]; then
            UPGRADE="yes"
            if [[ -n $P_IMG ]]; then
                pull_image "$P_IMG"
            fi
        else
            UPGRADE="no"
            if [[ -n $PREV_UTILS ]]; then
                echo >&2 "Error: No previously running utils image detected"
                exit 1
            fi
            UTILS_IMG="$PREV_UTILS"
            echo "Use old utils image: $UTILS_IMG"
        fi
    fi
}

function is_new_utils() {
    docker run --rm --entrypoint test "$UTILS_IMG" -e /root/launcher
}


################################################################################
# Main Business Logic                                                          #
################################################################################
ensure_directory "$HOME_DIR"
parse_general_conf
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
SNAPSHOT_DIR="$LOGS_DIR/snapshots"
ensure_directory "$SNAPSHOT_DIR"
DATA_DIR="$NETWORK_DIR/data"
ensure_directory "$DATA_DIR"
NETWORK_CONF="$NETWORK_DIR/$NETWORK.conf"
NETWORK_CONF_SAMPLE="$NETWORK_DIR/sample-$NETWORK.conf"
parse_network_conf


echo "🚀 Launching $NETWORK environment"
check_for_updates
if [[ -z $UTILS_IMG ]]; then
    echo >&2 "Error: Cannot determine which utils image to use"
    exit 1
fi
UTILS_ID=$(get_local_image_id "$UTILS_IMG")
if [[ -z $UTILS_ID ]]; then
    echo >&2 "Error: Image $UTILS_IMG is required"
    exit 1
fi
# backward compatible with old utils images
if is_new_utils; then
    RUN_SUFFIX="$UTILS_IMG"
else
    RUN_SUFFIX="--entrypoint python $UTILS_IMG -m launcher"
fi
docker run --rm -it \
--name "$(get_utils_name)" \
-v /var/run/docker.sock:/var/run/docker.sock \
-v "$HOME_DIR:/root/.xud-docker" \
-v "$NETWORK_DIR:/root/.xud-docker/$NETWORK" \
-v /:/mnt/hostfs \
-e LAUNCH_ID="$LAUNCH_ID" \
-e BRANCH="$BRANCH" \
-e NETWORK="$NETWORK" \
-e UPGRADE="$UPGRADE" \
-e DEV="$DEV" \
-e UTILS_IMG="$UTILS_IMG" \
-e UTILS_ID="$UTILS_ID" \
-e HOST_PWD="$PWD" \
-e HOST_HOME="$HOME" \
-e HOST_HOME_DIR="$HOME_DIR" \
-e HOST_NETWORK_DIR="$NETWORK_DIR" \
$RUN_SUFFIX "$@"
