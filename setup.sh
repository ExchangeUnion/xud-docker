#!/usr/bin/env bash

set -euo pipefail

function cleanup() {
    tput cnorm
    stty echo
}

trap cleanup EXIT

RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
RESET="\033[0m"

DEBUG=false
BRANCH=master
PROJECT_DIR=
HOME_DIR=~/.xud-docker
NETWORK=

function parse_arguments() {
    local OPTION VALUE
    while [[ $# -gt 0 ]]; do
        case $1 in
        "-d" | "--debug")
            DEBUG=true
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
                if ! curl -sf -o /dev/null https://api.github.com/repos/ExchangeUnion/xud-docker/git/refs/heads/$1; then
                    echo >&2 "❌ Branch \"$1\" does not exist"
                    exit 1
                fi
                VALUE=$1
            fi
            BRANCH=$VALUE
            ;;
        "--project-dir")
            OPTION=$1
            shift
            if [[ $# -eq 0 || $1 =~ ^- ]]; then
                echo >&2 "❌ Missing option value: $OPTION"
                exit 1
            fi
            PROJECT_DIR=$1
            ;;
        "--home-dir")
            OPTION=$1
            shift
            if [[ $# -eq 0 || $1 =~ ^- ]]; then
                echo >&2 "❌ Missing option value: $OPTION"
                exit 1
            fi
            HOME_DIR=$1
            ;;
        *)
            echo >&2 "❌ Invalid option: $1"
            exit 1
            ;;
        esac
        shift
    done
}

function check_directory() {
    local DIR=$1
    if [[ -f $DIR ]]; then
        echo >&2 "❌ $DIR is not a directory"
        exit 1
    fi

    if [[ ! -e $DIR ]]; then
        read -p "Would you like to create directory: $DIR? [Y/n] " -n 1 -r
        if [[ -n $REPLY ]]; then
            echo
        fi
        if [[ $REPLY =~ ^[Yy[:space:]]$ || -z $REPLY ]]; then
            mkdir -p "$DIR"
        else
            exit 1
        fi
    fi
}

function check_file() {
    local LOCAL_FILE=$1
    local REMOTE_FILE=$2
    local CACHE_FILE=$3
    local LOCAL_MD5 REMOTE_MD5 MD5

    if [[ $REMOTE_FILE =~ https ]]; then
        curl -sf "$REMOTE_FILE" >"$CACHE_FILE"
    else
        cp "$REMOTE_FILE" "$CACHE_FILE"
    fi

    if [[ ! -e $CACHE_FILE ]]; then
        echo >&2 "❌ Failed to cache the file: $CACHE_FILE"
        exit 1
    fi

    if [[ ! -e $LOCAL_FILE ]]; then
        echo -e "${RED}missing   ${RESET}"
        return
    fi

    if [[ $(uname) == "Darwin" ]]; then
        MD5=md5
    else
        MD5=md5sum
    fi

    LOCAL_MD5=$(cat "$LOCAL_FILE" | $MD5) #FIXME md5 value only
    REMOTE_MD5=$(cat "$CACHE_FILE" | $MD5)

    if [[ $LOCAL_MD5 == "$REMOTE_MD5" ]]; then
        echo -e "${GREEN}up-to-date${RESET}"
    else
        echo -e "${YELLOW}outdated  ${RESET}"
    fi
}

function human_readable_bytes() {
    local b=${1:-0}
    local d=''
    local s=0
    local S=(Bytes {K,M,G,T,P,E,Z,Y}iB)
    while ((b > 1024)); do
        d="$(printf ".%02d" $((b % 1024 * 100 / 1024)))"
        b=$((b / 1024))
        ((s++))
    done
    echo "$b$d ${S[$s]}"
}

function check_updates() {
    tput civis
    stty -echo
    local URL_PREFIX="https://raw.githubusercontent.com/ExchangeUnion/xud-docker/$BRANCH"
    #local MOVE="\033[s\033[1A\033[22C"
    local MOVE="\033[1A\033[22C"
    #local M_RESET="\033[u"
    local M_RESET="\033[1B\033[32D"
    local REMOTE_PREFIX=$PROJECT_DIR
    local SHA256 CREATED SIZE R_IMG NAME TAG TOKEN RESP R_SHA256 R_CREATED STATUS P_IMG
    local FILE_UPDATES=()
    local IMAGE_UPDATES=()
    local COMPOSE_FILE_HAS_UPDATE=false
    local MISSING_FILES=()

    echo "Checking files"

    if [[ -z $PROJECT_DIR ]]; then
        REMOTE_PREFIX=$URL_PREFIX
    fi

    echo " - banner file    ... "
    STATUS=$(check_file "$HOME_DIR/banner.txt" "$REMOTE_PREFIX/banner.txt" "$CACHE_DIR/banner.txt")
    if [[ $STATUS =~ outdated || $STATUS =~ missing ]]; then
        FILE_UPDATES+=("banner.txt")
        if [[ $STATUS =~ missing ]]; then
            MISSING_FILES+=("banner.txt")
        fi
    fi
    echo -en "${MOVE}${STATUS}${M_RESET}"

    echo " - init script    ... "
    STATUS=$(check_file "$HOME_DIR/init.sh" "$REMOTE_PREFIX/init.sh" "$CACHE_DIR/init.sh")
    if [[ $STATUS =~ outdated || $STATUS =~ missing ]]; then
        FILE_UPDATES+=("init.sh")
        if [[ $STATUS =~ missing ]]; then
            MISSING_FILES+=("init.sh")
        fi
    fi
    echo -en "${MOVE}${STATUS}${M_RESET}"

    echo " - status script  ... "
    STATUS=$(check_file "$HOME_DIR/status.py" "$REMOTE_PREFIX/status.py" "$CACHE_DIR/status.py")
    if [[ $STATUS =~ outdated || $STATUS =~ missing ]]; then
        FILE_UPDATES+=("status.py")
        if [[ $STATUS =~ missing ]]; then
            MISSING_FILES+=("status.py")
        fi
    fi
    echo -en "${MOVE}${STATUS}${M_RESET}"

    echo " - old status     ... "
    STATUS=$(check_file "$HOME_DIR/status.sh" "$REMOTE_PREFIX/status.sh" "$CACHE_DIR/status.sh")
    if [[ $STATUS =~ outdated || $STATUS =~ missing ]]; then
        FILE_UPDATES+=("status.sh")
        if [[ $STATUS =~ missing ]]; then
            MISSING_FILES+=("status.sh")
        fi
    fi
    echo -en "${MOVE}${STATUS}${M_RESET}"

    echo " - compose file   ... "
    STATUS=$(check_file "$NETWORK_DIR/docker-compose.yml" "$REMOTE_PREFIX/xud-$NETWORK/docker-compose.yml" "$CACHE_DIR/docker-compose.yml")
    if [[ $STATUS =~ outdated || $STATUS =~ missing ]]; then
        COMPOSE_FILE_HAS_UPDATE=true
        if [[ $STATUS =~ missing ]]; then
            MISSING_FILES+=("docker-compose.yml")
        fi
    fi
    echo -en "${MOVE}${STATUS}${M_RESET}"

    echo "Checking docker images"
    if [[ ! -e "$CACHE_DIR/docker-compose.yml" ]]; then
        echo >&2 "❌ Missing docker-compose.yml in $CACHE_DIR"
        exit 1
    fi
    IMAGES=$(grep "image" "$CACHE_DIR/docker-compose.yml" | sed -E 's/^.*: (.*)/\1/g' | sort | uniq | awk '!/:/{print $0 ":latest"}/:/{print}')

    for IMG in $(echo "$IMAGES" | xargs); do
        echo " - $IMG"
        SHA256=$(docker image inspect -f '{{.Config.Image}}' "$IMG" 2>/dev/null | sed -E 's/sha256://g' || true)
        if [[ -z $SHA256 ]]; then
            echo -e "   Status: ${RED}missing${RESET}"

            # Check if there is any branch images
            # TODO remove duplicated codes
            if [[ $BRANCH == "master" ]]; then
                R_IMG=$IMG
            else
                R_IMG="${IMG}__${BRANCH//\//-}"
            fi
            NAME=$(echo "$R_IMG" | cut -d':' -f1)
            TAG=$(echo "$R_IMG" | cut -d':' -f2)
            TOKEN=$(curl -sf "https://auth.docker.io/token?service=registry.docker.io&scope=repository:$NAME:pull" | sed -E 's/^.*"token":"([^,]*)",.*$/\1/g')
            if ! curl -sf -o /dev/null -H "Authorization: Bearer $TOKEN" "https://registry-1.docker.io/v2/$NAME/manifests/$TAG"; then
                R_IMG=$IMG
                TAG=$(echo "$IMG" | cut -d':' -f2)
            fi

            IMAGE_UPDATES+=("$R_IMG")
            continue
        fi
        echo "   SHA-256: $SHA256"
        CREATED=$(docker image inspect -f '{{index .Config.Labels "com.exchangeunion.image.created"}}' "$IMG")
        echo "   Created: $CREATED"
        SIZE=$(docker image inspect -f '{{.Size}}' "$IMG")
        echo "   Size: $SIZE ($(human_readable_bytes "$SIZE"))"
        if [[ $BRANCH == "master" ]]; then
            R_IMG=$IMG
        else
            R_IMG="${IMG}__${BRANCH//\//-}"
        fi
        NAME=$(echo "$R_IMG" | cut -d':' -f1)
        TAG=$(echo "$R_IMG" | cut -d':' -f2)
        TOKEN=$(curl -sf "https://auth.docker.io/token?service=registry.docker.io&scope=repository:$NAME:pull" | sed -E 's/^.*"token":"([^,]*)",.*$/\1/g')
        if ! curl -sf -o /dev/null -H "Authorization: Bearer $TOKEN" "https://registry-1.docker.io/v2/$NAME/manifests/$TAG"; then
            R_IMG=$IMG
            TAG=$(echo "$IMG" | cut -d':' -f2)
        fi
        echo "   * Remote image (registry-1.docker.io): $R_IMG"
        RESP=$(curl -sf -H "Authorization: Bearer $TOKEN" "https://registry-1.docker.io/v2/$NAME/manifests/$TAG")
        RESP=$(echo "$RESP" | grep v1Compatibility | head -1 | sed 's/^.*v1Compatibility":/printf/g')
        RESP=$(eval "$RESP")
        R_SHA256=$(echo "$RESP" | sed -E 's/.*sha256:([a-z0-9]+).*/\1/g')
        R_CREATED=$(echo "$RESP" | sed -E 's/.*com.exchangeunion.image.created":"([^"]*)".*/\1/g')
        echo "   SHA-256: $R_SHA256"
        echo "   Created: $R_CREATED"
        if [[ $SHA256 == "$R_SHA256" ]]; then
            STATUS="${GREEN}up-to-date${RESET}"
        else
            if [[ $CREATED > $R_CREATED ]]; then
                STATUS="${BLUE}newer${RESET}"
            else
                STATUS="${YELLOW}outdated${RESET}"
            fi
        fi
        if [[ $STATUS =~ outdated || $STATUS =~ missing ]]; then
            IMAGE_UPDATES+=("$R_IMG")
        fi
        echo -e "   Status: ${YELLOW}${STATUS}${RESET}"
    done

    tput cnorm
    stty echo

    if [[ ${#FILE_UPDATES[@]} -gt 0 || ${#IMAGE_UPDATES[@]} -gt 0 || $COMPOSE_FILE_HAS_UPDATE == "true" ]]; then
        read -p "A new version is available. Would you like to upgrade (Warning: this may restart your environment and cancel all open orders)? [Y/n] " -n 1 -r
        if [[ -n $REPLY ]]; then
            echo
        fi
        if [[ $REPLY =~ ^[Yy[:space:]]$ || -z $REPLY ]]; then
            if [[ ${#FILE_UPDATES[@]} -gt 0 ]]; then
                for FILE in "${FILE_UPDATES[@]}"; do
                    echo "📄 Updating file: $FILE"
                    cp "$CACHE_DIR/$FILE" "$HOME_DIR/$FILE"
                done
            fi
            if [[ $COMPOSE_FILE_HAS_UPDATE == "true" || ${#IMAGE_UPDATES[@]} -gt 0 ]]; then
                if docker ps --format '{{.Names}}' | grep -q "${NETWORK}_"; then
                    echo "🌙 Shutting down $NETWORK environment"
                    if [[ -e docker-compose.yml ]]; then
                        $DOCKER_COMPOSE down
                    else
                        echo "⚠️ The docker-compose.yml file is missing and there are still some \"${NETWORK}_\" prefixed containers running."
                        docker ps --filter name=$NETWORK -q | xargs docker stop >/dev/null
                        docker ps --filter name=$NETWORK -q -a | xargs docker rm >/dev/null
                        docker network rm ${NETWORK}_default >/dev/null
                    fi
                fi
                if [[ $COMPOSE_FILE_HAS_UPDATE == "true" ]]; then
                    echo "📄 Updating file: $NETWORK_DIR/docker-compose.yml"
                    cp "$CACHE_DIR/docker-compose.yml" "$NETWORK_DIR/docker-compose.yml"
                fi
                if [[ ${#IMAGE_UPDATES[@]} -gt 0 ]]; then
                    for P_IMG in "${IMAGE_UPDATES[@]}"; do
                        echo "📦 Updating image: $P_IMG"
                        if ! docker pull "$P_IMG" 2>/dev/null; then
                            echo >&2 "❌ Cannot pull $P_IMG"
                            exit 1
                        fi
                        if [[ $P_IMG =~ __ ]]; then
                            IMG=$(echo "$IMG" | sed -E 's/__.*//g')
                            echo "Re-tagging image $P_IMG to $IMG"
                            docker tag "$P_IMG" "$IMG"
                        fi
                    done
                fi
            fi
        else
            if [[ ${#MISSING_FILES[@]} -gt 0 ]]; then
                echo >&2 "❌ Missing necessary launching files: ${MISSING_FILES[*]}"
                exit 1
            fi
        fi
    fi
}

function no_lnd_wallet() {
    local CHAIN=$1
    local SERVICE
    local RESULT

    case $CHAIN in
    bitcoin)
        SERVICE="lndbtc"
        ;;
    litecoin)
        SERVICE="lndltc"
        ;;
    esac

    RESULT=""

    while [[ -z $RESULT || $RESULT =~ "ERROR" ]]; do
        RESULT=$($DOCKER_COMPOSE exec $SERVICE bash -c 'netstat -ant | grep LISTEN | grep 10009')
        sleep 1
    done

    RESULT=$($DOCKER_COMPOSE exec $SERVICE lncli -n $NETWORK -c "$CHAIN" getinfo | grep "unable to read macaroon path")
    [[ -n $RESULT ]]
}

function no_wallets() {
    no_lnd_wallet bitcoin || no_lnd_wallet litecoin
}

function xucli_create_wrapper() {
    local LINE=""
    local COUNTER=0
    local OK=false
    local ERROR=""
    local RETRY=""
    while [[ $OK == "false" && $COUNTER -lt 3 && -z $ERROR ]]; do
        ((COUNTER++))
        ERROR=""
        shopt -s nocasematch
        while read -n 1; do
            if [[ $REPLY == $'\n' || $REPLY == $'\r' ]]; then
                if [[ ! $LINE =~ "<hide>" ]]; then
                    echo -e "$LINE\r"
                fi
                LINE=""
            else
                LINE="$LINE$REPLY"
                if [[ $LINE =~ 'password: ' ]]; then
                    echo -n "$LINE"
                    LINE=""
                elif [[ $LINE =~ getenv ]]; then
                    LINE="<hide>"
                elif [[ $LINE =~ "Passwords do not match, please try again" ]]; then
                    RETRY="passwords do not match"
                    ERROR=""
                elif [[ $LINE =~ "password must be at least 8 characters" ]]; then
                    RETRY="invalid password"
                    ERROR=""
                elif [[ $LINE =~ "xud was initialized without a seed because no wallets could be initialized" ]]; then
                    ERROR="no wallets could be initialized"
                elif [[ $LINE =~ "error" ]]; then
                    ERROR="unexpected error"
                elif [[ $LINE =~ "it is your ONLY backup in case of data loss" ]]; then
                    OK="true"
                fi
            fi
        done < <($DOCKER_COMPOSE exec xud xucli create)
        shopt -u nocasematch
        # We use process substitution here to force the while loop to run in the main shell (not a subshell). So we can
        # preserve the modification of ERROR after the while command exits which a subshell cannot.
        #
        # Ref. https://stackoverflow.com/questions/5760640/left-side-of-pipe-is-the-subshell
        # From the bash man page: "Each command in a pipeline is executed as a separate process (i.e., in a subshell)."
        #
        # The exit code of "while read" is decided by pipelined or <(...) "create" command
        # For bash if a script is terminated by SIGINT then the exit code is 130 (128 + 2)
        # But for some other programs their exit code may not follow this rule. In our case "docker-compose exec xud xucli create"
        # returns 0 when it is terminated by SIGINT
        if [[ -z $RETRY && -z $ERROR && $OK == "false" ]]; then
            echo "^C"
            ERROR="sigint"
        fi
    done
    [[ -z $ERROR && $OK == "true" ]]
}

function check_wallets() {
    if no_wallets; then
        local xucli="$DOCKER_COMPOSE exec xud xucli"

        #TODO NOT sure if we need to wait lndbtc, lndltc and raiden to be ready here
        echo -n "⏳ Waiting for xud to be ready"
        while $xucli getinfo | grep -q "UNIMPLEMENTED"; do
            echo -n "."
            sleep 3
        done
        echo

        if ! xucli_create_wrapper; then
            echo "🌙 Shutting down $NETWORK environment"
            docker-compose down
            exit 1
        fi

        while true; do
            read -p "YOU WILL NOT BE ABLE TO DISPLAY YOUR XUD SEED AGAIN. Press ENTER to continue..." -n 1 -r
            if [[ -z $REPLY ]]; then
                break
            else
                echo
            fi
        done
    fi
}

function get_all_services() {
    grep -A 999 services docker-compose.yml | sed -nE 's/^  ([a-z]+):$/\1/p' | sort | paste -sd " " -
}

function get_up_services() {
    # grep ${network} in case docekr-compose ps Ports column has multiple rows
    $DOCKER_COMPOSE ps | grep "$NETWORK" | grep Up | awk '{print $1}' | sed -E "s/${NETWORK}_//g" | sed -E 's/_1//g' | sort | paste -sd " " -
}

function is_all_containers_up() {
    local UP ALL
    UP=$(get_up_services)
    ALL=$(get_all_services)
    [[ $UP == "$ALL" ]]
}

function launch_xudctl() {
    if ! is_all_containers_up; then
        echo "🚀 Launching $NETWORK environment"
        $DOCKER_COMPOSE up -d
    fi

    if [[ $NETWORK == 'testnet' || $NETWORK == 'mainnet' ]]; then
        check_wallets
    fi

    XUD_DOCKER_HOME="$HOME_DIR" XUD_NETWORK="$NETWORK" XUD_NETWORK_DIR="$NETWORK_DIR" bash --init-file $HOME_DIR/init.sh
}

parse_arguments "$@"

if [[ $DEBUG == "true" ]]; then
    set -x
fi

if ! command -v bash >/dev/null; then
    echo >&2 "❌ Missing bash"
    exit 1
fi

if ! command -v docker >/dev/null; then
    echo >&2 "❌ Missing docker"
    exit 1
fi

if ! command -v docker-compose >/dev/null; then
    echo >&2 "❌ Missing docker-compose"
    exit 1
fi

echo "1) Simnet"
echo "2) Testnet"
echo "3) Mainnet"
read -p "Please choose the network: " -r
shopt -s nocasematch
REPLY=$(echo "$REPLY" | awk '{$1=$1;print}') # trim whitespaces
case $REPLY in
1 | simnet)
    NETWORK=simnet
    NETWORK_DIR=$HOME_DIR/simnet
    ;;
2 | testnet)
    NETWORK=testnet
    NETWORK_DIR=$HOME_DIR/testnet
    ;;
3 | mainnet)
    NETWORK=mainnet
    NETWORK_DIR=$HOME_DIR/mainnet
    ;;
*)
    echo >&2 "❌ Invalid network: $REPLY"
    exit 1
    ;;
esac
shopt -u nocasematch

DOCKER_COMPOSE="docker-compose -p $NETWORK"

check_directory "$HOME_DIR"
HOME_DIR=$(realpath "$HOME_DIR")
CACHE_DIR=$HOME_DIR/cache
if [[ ! -e $CACHE_DIR ]]; then
    mkdir "$CACHE_DIR"
fi
check_directory "$NETWORK_DIR"
NETWORK_DIR=$(realpath "$NETWORK_DIR")

cd "$NETWORK_DIR"
if [[ ! -e lnd.env ]]; then touch lnd.env; fi
check_updates
launch_xudctl
