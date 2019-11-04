#!/bin/bash

set -euo pipefail
set -m

function hide_cursor() {
    tput civis
    stty -echo
}

function show_cursor() {
    tput cnorm
    stty echo
}

function cleanup() {
    show_cursor
}

trap cleanup EXIT

if ! command -v bc >/dev/null; then
    echo >&2 "Missing bc"
    exit 1
fi

if ! command -v docker-compose >/dev/null; then
    echo >&2 "Missing docker-compose"
    exit 1
fi

if [[ -z ${XUD_NETWORK:-} ]]; then
    echo >&2 "Missing XUD_NETWORK"
    exit 1
fi

if [[ -z ${XUD_DOCKER_HOME:-} ]]; then
    echo >&2 "Missing XUD_DOCKER_HOME"
    exit 1
fi

if [[ ${DEBUG:-} == "verbose" ]]; then
    set -x
fi

DOCKER_COMPOSE="docker-compose -p $XUD_NETWORK"
# using -T to solve docker-compose error:
# the input device is not a TTY
# ref. https://github.com/docker/compose/issues/5696
DOCKER_COMPOSE_EXEC="$DOCKER_COMPOSE exec -T"
CACHE_DIR="$XUD_DOCKER_HOME/cache"

bitcoind="$DOCKER_COMPOSE_EXEC bitcoind bitcoin-cli -rpcuser=xu -rpcpassword=xu"
litecoind="$DOCKER_COMPOSE_EXEC litecoind litecoin-cli -rpcuser=xu -rpcpassword=xu"
lndbtc="$DOCKER_COMPOSE_EXEC lndbtc lncli -n $XUD_NETWORK -c bitcoin"
lndltc="$DOCKER_COMPOSE_EXEC lndltc lncli -n $XUD_NETWORK -c litecoin"
geth="$DOCKER_COMPOSE_EXEC geth geth"
xud="$DOCKER_COMPOSE_EXEC xud xucli"
btcd="$DOCKER_COMPOSE_EXEC btcd btcctl --$XUD_NETWORK --rpcuser=xu --rpcpass=xu"
ltcd="$DOCKER_COMPOSE_EXEC ltcd ltcctl --$XUD_NETWORK --rpcuser=xu --rpcpass=xu"

if [ "$XUD_NETWORK" != "mainnet" ]; then
    bitcoind+=" -$XUD_NETWORK"
    litecoind+=" -$XUD_NETWORK"
    geth+=" --$XUD_NETWORK"
fi

function calculate_percentage() {
    if [[ $# -ne 2 ]]; then
        echo >&2 "[calculate_percentage] two arguments required: $*"
        return 1
    fi
    if [[ ! $1 =~ ^[0-9.]+$ ]]; then
        echo >&2 "[calculate_percentage] 1st argument should be a number: $1"
        return 1
    fi
    if [[ ! $2 =~ ^[0-9.]+$ ]]; then
        echo >&2 "[calculate_percentage] 2nd argument should be a number: $2"
        return 1
    fi
    awk -v x="$1" -v y="$2" 'BEGIN{z=x/y*100-0.005; z=z>0?z:0; printf "%.2f%%\n", z}'
}

function status_text() {
    if [[ $# -lt 2 ]]; then
        echo >&2 "Missing parameters: $*"
        exit 1
    fi

    local CURRENT=$1
    local TOTAL=$2

    if [[ $CURRENT -gt $TOTAL ]]; then
        echo "Syncing 99.99%"
    else
        if [[ $CURRENT -eq $TOTAL ]]; then
            echo "Ready"
        else
            # LC_NUMERIC="en_US.UTF-8"
            printf "Syncing %s (%d/%d)\n" "$(calculate_percentage "$CURRENT" "$TOTAL")" "$CURRENT" "$TOTAL"
        fi
    fi
}

function status_text2() {
    if [[ $# -lt 2 ]]; then
        echo >&2 "Missing parameters: $*"
        exit 1
    fi

    local CURRENT=$1
    local TOTAL=$2

    if [[ $CURRENT -eq $TOTAL ]]; then
        echo "Ready"
    else
        echo "Waiting for sync"
    fi
}

function check_container() {
    local CONTAINER=$1
    local ERROR
    if ! $DOCKER_COMPOSE ps | grep Up | grep "$CONTAINER" >/dev/null 2>&1; then
        if [[ $CONTAINER == "litecoind" ]]; then
            # 2019-11-04T12:51:13Z ERROR: ReadBlockFromDisk: Errors in block header at CBlockDiskPos(nFile=0, nPos=1860463)
            # 2019-11-04T12:51:13Z *** ThreadSync: Failed to read block 3ca67472db1cdcab96aa95dccd991af117e9261dc41f6eca9a841fb37574c433 from disk
            # 2019-11-04T12:51:13Z Error: Error: A fatal internal error occurred, see debug.log for details
            ERROR=$($DOCKER_COMPOSE logs --tail=50 litecoind | grep -A 2 ReadBlockFromDisk)
            if [[ -n $ERROR ]]; then
                if [[ $(echo "$ERROR" | sed -n '2p') =~ "Failed to read block" && $(echo "$ERROR" | sed -n '3p') =~ "A fatal internal error occurred" ]]; then
                    echo "Data corruption"
                    return 1
                fi
            fi
        fi
        echo "Container down"
        return 1
    fi
    return 0
}

function btcd_status() {
    local INFO ARGS
    INFO=$($btcd getblockchaininfo || return 1)
    ARGS=$(echo "$INFO" | grep -A 1 blocks | sed -nE 's/[^0-9]*([0-9]+).*/\1/p' | paste -sd ' ' -)
    if [[ -z $ARGS ]]; then
        echo "$INFO" | tail -1
    else
        # shellcheck disable=SC2086
        status_text $ARGS
    fi
}

function ltcd_status() {
    local INFO ARGS
    INFO=$($ltcd getblockchaininfo || return 1)
    ARGS=$(echo "$INFO" | grep -A 1 blocks | sed -nE 's/[^0-9]*([0-9]+).*/\1/p' | paste -sd ' ' -)
    if [[ -z $ARGS ]]; then
        echo "$INFO" | tail -1
    else
        # shellcheck disable=SC2086
        status_text $ARGS
    fi
}

function bitcoind_status() {
    local INFO ARGS
    INFO=$($bitcoind getblockchaininfo || return 1)
    ARGS=$(echo "$INFO" | grep -A 1 blocks | sed -nE 's/[^0-9]*([0-9]+).*/\1/p' | paste -sd ' ' -)
    if [[ -z $ARGS ]]; then
        echo "$INFO" | tail -1
    else
        # shellcheck disable=SC2086
        status_text $ARGS
    fi
}

function litecoind_status() {
    local INFO ARGS
    INFO=$($litecoind getblockchaininfo || return 1)
    ARGS=$(echo "$INFO" | grep -A 1 blocks | sed -nE 's/[^0-9]*([0-9]+).*/\1/p' | paste -sd ' ' -)
    if [[ -z $ARGS ]]; then
        echo "$INFO" | tail -1
    else
        # shellcheck disable=SC2086
        status_text $ARGS
    fi
}

function get_lnd_status() {
    local CHAIN=$1
    local INFO CLI LAST SERVICE
    case $CHAIN in
        bitcoin) CLI=$lndbtc; SERVICE=lndbtc;;
        litecoin) CLI=$lndltc; SERVICE=lndltc;;
    esac
    if INFO=$($CLI getinfo 2>&1); then
        if echo "$INFO" | grep -q '"synced_to_chain": true'; then
            echo "Ready"
        else
            echo "Waiting for sync"
        fi
    else
        if [[ $INFO =~ "Wallet is encrypted" ]]; then
            # Make sure this line is the last line of the log: [INF] LTND: Waiting for wallet encryption password.
            # Use `lncli create` to create a wallet, `lncli unlock` to unlock an existing wallet, or `lncli change
            # password` to change the password of an existing wallet and unlock it.
            LAST=$($DOCKER_COMPOSE_EXEC $SERVICE tail -1 "/root/.lnd/logs/$CHAIN/$XUD_NETWORK/lnd.log")
            if [[ $LAST =~ "Waiting for wallet encryption password" ]]; then
                echo "Wallet locked. Unlock with xucli unlock."
            else
                echo "oops >_<"
            fi
        else
            echo "oops >_<"
        fi
    fi
}

function lndbtc_status() {
    get_lnd_status bitcoin
}

function lndltc_status() {
    get_lnd_status litecoin
}

function nocolor() {
    sed -r "s/\x1b\[([0-9]{1,2}(;[0-9]{1,2})?)?m//g"
}

function geth_status() {
    local SYNCING
    SYNCING=$($geth --exec 'eth.syncing' attach 2>/dev/null)

    if [[ $SYNCING != "false" ]]; then
        SYNCING=$(echo "$SYNCING" | nocolor | grep -A 1 currentBlock | sed -nE 's/[^0-9]*([0-9]+).*/\1/p' | paste -sd ' ' -)
	      # shellcheck disable=SC2086
	      status_text $SYNCING
    else
        # If 'eth.syncing' is false and 'eth.blockNumber' is 0 the sync has not started yet
        if [[ $($geth --exec 'eth.blockNumber' attach 2>/dev/null) == "0" ]]; then
            echo "Waiting for sync"
        else
    	      echo "Ready"
        fi
    fi
}

function raiden_status() {
    local SYNC
    SYNC=$($DOCKER_COMPOSE_EXEC raiden curl -is http://localhost:5001/api/v1/tokens | grep "200 OK")
    if [[ -z $SYNC ]]; then
        echo "Waiting for sync"
    else
        echo "Ready"
    fi
}

function xud_status() {
    local INFO LNDBTC_OK LNDLTC_OK RAIDEN_OK
    INFO=$($xud getinfo -j 2>/dev/null)
    LNDBTC_OK=$(echo "$INFO" | grep -A2 BTC | grep error | grep '""')
    LNDLTC_OK=$(echo "$INFO" | grep -A2 LTC | grep error | grep '""')
    RAIDEN_OK=$(echo "$INFO" | grep -A1 raiden | grep error | grep '""')

    if [[ -n $LNDBTC_OK && -n $LNDLTC_OK  && -n $RAIDEN_OK ]]; then
        echo "Ready"
    else
        echo "Waiting for sync"
    fi
}

SIMNET_SERVICES=(lndbtc ltcd lndltc raiden xud)
TESTNET_SERVICES=(bitcoind lndbtc litecoind lndltc geth raiden xud)
MAINNET_SERVICES=(bitcoind lndbtc litecoind lndltc geth raiden xud)

function get_status() {
    local SERVICE=$1
    local ERR_FILE ERROR
    ERR_FILE="${CACHE_DIR}/${XUD_NETWORK}_${service}.status.err"
    rm -f "$ERR_FILE"
    # shellcheck disable=SC2086
    check_container "$SERVICE" && ${SERVICE}_status 2>"$ERR_FILE"
    ERROR=$(cat "$ERR_FILE" 2>/dev/null || echo "")
    if [[ -n $ERROR ]]; then
        if [[ ($SERVICE == "bitcoind" || $SERVICE == "litecoind" || $SERVICE == "btcd" || $SERVICE == "ltcd") && $ERROR =~ "error message" ]]; then
            echo "$ERROR" | tail -1
        else
            echo "oops >_<"
        fi
    fi
    echo "END"
}

function get_display_name() {
    local SERVICE=$1
    case $SERVICE in
        btcd|bitcoind) echo "btc";;
        ltcd|litecoind) echo "ltc";;
        lndbtc) echo "lndbtc";;
        lndltc) echo "lndltc";;
        geth) echo "eth";;
        raiden) echo "raiden";;
        xud) echo "xud";;
    esac
}

BRIGHT_BLACK="\033[90m"
BLUE="\033[34m"
RESET="\033[0m"
BOLD="\033[30;1m"

function supports_animation() {
    [[ ${DEBUG:-} != "true" && ${DEBUG:-} != "verbose" ]] && tty -s
}

function get_all_status() {
    local SERVICES=()
    local FILE LAST STATUS COUNTER INDEX N NAME

    case $XUD_NETWORK in
        simnet) SERVICES=("${SIMNET_SERVICES[@]}");;
        testnet) SERVICES=("${TESTNET_SERVICES[@]}");;
        mainnet) SERVICES=("${MAINNET_SERVICES[@]}");;
    esac

    for service in ${SERVICES[*]}; do
        FILE="${CACHE_DIR}/${XUD_NETWORK}_${service}.status"
        echo "BEGIN" > "$FILE"
        echo -e "$(get_status "$service")" >> "$FILE" &
    done

    supports_animation && hide_cursor

    echo -e "${BRIGHT_BLACK}┌─────────┬──────────────────────────────────────────┐${RESET}"
    echo -e "${BRIGHT_BLACK}│${RESET} ${BOLD}SERVICE${RESET} ${BRIGHT_BLACK}│${RESET} ${BOLD}STATUS${RESET}                                   ${BRIGHT_BLACK}│${RESET}"

    COUNTER=0
    INDEX=0
    while true; do
        if supports_animation && [[ $INDEX -gt 0 ]] ; then
            N=${#SERVICES[@]}
            echo -e "\033[$((N*2+2))A"
        fi
        for service in ${SERVICES[*]}; do
            FILE="${CACHE_DIR}/${XUD_NETWORK}_${service}.status"
            LAST=$(tail -1 "$FILE")
            if [[ $LAST == "BEGIN" ]]; then
                STATUS="fetching"
                N=$((3-INDEX%7))
                N=${N#-}
                # shellcheck disable=SC2034
                for i in $(seq 1 $N); do
                    STATUS="$STATUS."
                done
            elif [[ $LAST == "END" ]]; then
                STATUS=$(tail -2 "$FILE" | head -1)
                ((COUNTER=COUNTER+1))
                echo "---" >> "$FILE"
            elif [[ $LAST == "---" ]]; then
                STATUS=$(tail -3 "$FILE" | head -1)
            else
                STATUS=$LAST
            fi
            if [[ $STATUS =~ fetching ]]; then
                STATUS=$(printf "$BRIGHT_BLACK%-40s$RESET" "$STATUS")
            else
                STATUS=$(printf "%-40s" "$STATUS")
            fi
            NAME=$(printf "%-7s" "$(get_display_name "$service")")
            echo -e "${BRIGHT_BLACK}├─────────┼──────────────────────────────────────────┤${RESET}"
            echo -e "${BRIGHT_BLACK}│${RESET} ${BLUE}${NAME}${RESET} ${BRIGHT_BLACK}│${RESET} ${STATUS} ${BRIGHT_BLACK}│${RESET}"
        done
        echo -e "${BRIGHT_BLACK}└─────────┴──────────────────────────────────────────┘${RESET}"
        ((INDEX=INDEX+1))
        if [[ $COUNTER -ge ${#SERVICES[@]} ]]; then
            break
        fi
        sleep 0.5
    done

}

get_all_status
