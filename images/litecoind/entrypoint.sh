#!/bin/bash

set -euo pipefail

LITECOIN_DIR=$HOME/.litecoin

if [[ $NETWORK == "testnet" ]]; then
    LOGFILE=$LITECOIN_DIR/testnet4/debug.log
    DEFAULT_RPC_PORT=19332
elif [[ $NETWORK == "mainnet" ]]; then
    LOGFILE=$LITECOIN_DIR/debug.log
    DEFAULT_RPC_PORT=9332
fi

EXIT_CODE=0
EXIT_REASON="EMPTY"
RETRY=0
DEFAULT_MAX_RETRY=3
DEFAULT_RPC_USER="xu"
DEFAULT_RPC_PASSWORD="xu"
DEFAULT_RETRY_DELAY=3
ERRFILE="/tmp/launch.err"

DEFAULT_OPTS=(
    "-server"
    "-rpcuser=${RPC_USER:-${DEFAULT_RPC_USER}}"
    "-rpcpassword=${RPC_PASSWORD:-${DEFAULT_RPC_PASSWORD}}"
    "-disablewallet"
    "-txindex"
    "-zmqpubrawblock=tcp://0.0.0.0:29332"
    "-zmqpubrawtx=tcp://0.0.0.0:29333"
    "-logips"
    "-rpcport=${RPC_PORT:-${DEFAULT_RPC_PORT}}"
    "-rpcallowip=::/0"
    "-rpcbind=0.0.0.0"
)

if [[ $NETWORK == "testnet" ]]; then
    DEFAULT_OPTS+=("-testnet")
fi

OPTS=("${DEFAULT_OPTS[@]}")

function start_litecoind() {
    rm -f "$LOGFILE" "$ERRFILE"
    # shellcheck disable=SC2068
    # Starting litecoind in background because it makes trap commands not working when running in foreground.
    # Tried >/dev/null, exec (process replacing) which are helpless to this problem.
    # The root reason of this problem is still not clear.
    litecoind ${OPTS[@]} 2>"$ERRFILE" &
    wait
}

function stop_litecoind() {
    case $NETWORK in
    testnet)
        litecoin-cli -rpcuser="${RPC_USER:-${DEFAULT_RPC_USER}}" -rpcpassword="${RPC_PASSWORD:-${DEFAULT_RPC_PASSWORD}}" -testnet stop
        ;;
    mainnet)
        litecoin-cli -rpcuser="${RPC_USER:-${DEFAULT_RPC_USER}}" -rpcpassword="${RPC_PASSWORD:-${DEFAULT_RPC_PASSWORD}}" stop
        ;;
    esac
    wait
}

function analyze_exit_reason() {
    if [[ -e $LOGFILE ]]; then
        ERROR=$(grep -A 2 ReadBlockFromDisk "$LOGFILE" || echo "")
        if [[ -n $ERROR ]]; then
            if [[ $(echo "$ERROR" | sed -n '2p') =~ "Failed to read block" && $(echo "$ERROR" | sed -n '3p') =~ "A fatal internal error occurred" ]]; then
                EXIT_REASON="CORRUPTED_DATA"
            fi
        fi
    fi
    if [[ $EXIT_REASON == "EMPTY" ]]; then
        if [[ -e $ERRFILE ]]; then
            EXIT_REASON=$(cat $ERRFILE)
        fi
    fi
}

function trigger_post_exit_actions() {
    if [[ $RETRY -ge $((${MAX_RETRY:-${DEFAULT_MAX_RETRY}} - 1)) ]]; then
        RUNNING=false
        EXIT_CODE=1
    fi

    case $EXIT_REASON in
        CORRUPTED_DATA)
            OPTS=("${DEFAULT_OPTS[@]}")
            OPTS+=("-reindex-chainstate")
            ;;
        *)
            echo "Fatal exit reason ($EXIT_REASON). Restart litecoind in ${RETRY_DELAY:-${DEFAULT_RETRY_DELAY}} seconds ($RETRY retry)"
            sleep "${RETRY_DELAY:-${DEFAULT_RETRY_DELAY}}"
            OPTS=("${DEFAULT_OPTS[@]}")
            OPTS+=("-reindex")
            ;;
    esac

    # https://stackoverflow.com/questions/6877012/incrementing-a-variable-triggers-exit-in-bash-4-but-not-in-bash-3
    ((RETRY++)) || true
}

RUNNING=true

trap 'echo :: SIGINT; stop_litecoind' SIGINT
trap 'echo :: SIGTERM; stop_litecoind' SIGTERM

function do_loop() {
    echo ":: Launch ($((RETRY+1)))"
    start_litecoind
    analyze_exit_reason
    trigger_post_exit_actions
}

while [[ $RUNNING == "true" ]]; do
    do_loop
done

exit $EXIT_CODE
