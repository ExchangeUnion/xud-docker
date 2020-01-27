#!/bin/bash

export PS1="$NETWORK > "
export GRACEFUL_SHUTDOWN_TIMEOUT=180

case $NETWORK in
mainnet)
    alias bitcoin-cli="docker exec mainnet_bitcoind_1 bitcoin-cli -rpcuser=xu -rpcpassword=xu"
    alias litecoin-cli="docker exec mainnet_litecoind_1 litecoin-cli -rpcuser=xu -rpcpassword=xu"
    alias lndbtc-lncli="docker exec mainnet_lndbtc_1 lncli -n mainnet -c bitcoin"
    alias lndltc-lncli="docker exec mainnet_lndltc_1 lncli -n mainnet -c litecoin"
    alias geth="docker exec mainnet_geth_1 geth"
    alias raiden-curl="docker exec mainnet_raiden_1 curl"
    CONTAINERS=(mainnet_bitcoind_1 mainnet_litecoind_1 mainnet_lndbtc_1 mainnet_lndltc_1 mainnet_geth_1 mainnet_raiden_1 mainnet_xud_1)
    NODES=(bitcoind litecoind lndbtc lndltc geth raiden xud)
    ;;
testnet)
    alias bitcoin-cli="docker exec testnet_bitcoind_1 bitcoin-cli -testnet -rpcuser=xu -rpcpassword=xu"
    alias litecoin-cli="docker exec testnet_litecoind_1 litecoin-cli -testnet -rpcuser=xu -rpcpassword=xu"
    alias lndbtc-lncli="docker exec testnet_lndbtc_1 lncli -n testnet -c bitcoin"
    alias lndltc-lncli="docker exec testnet_lndltc_1 lncli -n testnet -c litecoin"
    alias geth="docker exec testnet_geth_1 geth --testnet"
    alias raiden-curl="docker exec testnet_raiden_1 curl"
    CONTAINERS=(testnet_bitcoind_1 testnet_litecoind_1 testnet_lndbtc_1 testnet_lndltc_1 testnet_geth_1 testnet_raiden_1 testnet_xud_1)
    NODES=(bitcoind litecoind lndbtc lndltc geth raiden xud)
    ;;
simnet)
    alias ltcctl="docker exec simnet_ltcd_1 ltcctl --simnet --rpcuser=xu --rpcpass=xu"
    alias lndbtc-lncli="docker exec simnet_lndbtc_1 lncli -n simnet -c bitcoin"
    alias lndltc-lncli="docker exec simnet_lndltc_1 lncli -n simnet -c litecoin"
    alias raiden-curl="docker exec simnet_raiden_1 curl"
    CONTAINERS=(simnet_ltcd_1 simnet_lndbtc_1 simnet_lndltc_1 simnet_raiden_1 simnet_xud_1)
    NODES=(ltcd lndbtc lndltc raiden xud)
    ;;
esac

function utils_run() {
    docker run --rm -it \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v "$HOME_DIR":/root/.xud-docker \
        -v "$NETWORK_DIR":/root/.xud-docker/$NETWORK \
        -e HOME_DIR="$HOME_DIR" \
        -e NETWORK="$NETWORK" \
        -e NETWORK_DIR="$NETWORK_DIR" \
        -e LAUNCH_ARGS="$LAUNCH_ARGS" \
        --entrypoint python \
        exchangeunion/utils \
        -m launcher.command $@
}

function get_stopped_conainers() {
    utils_run get_stopped_containers
}
function get_running_containers() {
    utils_run get_running_containers
}

function expand_args() {
    local LAST
    ARGS=("$@")
    LAST_INDEX=$((${#ARGS[@]} - 1))
    LAST="${NETWORK}_${ARGS[$LAST_INDEX]}_1"
    ARGS_BEFORE=("${ARGS[@]:0:$LAST_INDEX}")
    echo "${ARGS_BEFORE[@]}" "$LAST"
}

function logs() {
    docker logs $(expand_args "$@")
}
complete -W "${NODES[*]}" logs

function start() {
    docker start $(expand_args "$@")
}
complete -F get_stopped_conainers start

function stop() {
    docker stop -t $GRACEFUL_SHUTDOWN_TIMEOUT $(expand_args "$@")
}
complete -F get_running_conainers stop

function restart() {
    docker restart -t $GRACEFUL_SHUTDOWN_TIMEOUT $(expand_args "$@")
}
complete -F get_running_conainers restart

function report() {
    :
}

function status() {
    utils_run status
}

function update() {
    utils_run update
}

function down() {
    for container in "${CONTAINERS[@]}"; do
        echo "Stopping $container"
        docker stop $container >/dev/null
    done
    for container in "${CONTAINERS[@]}"; do
        echo "Removing $container"
        docker rm $container >/dev/null
    done
    echo "Removing network ${NETWORK}_default"
    docker network rm ${NETWORK}_default >/dev/null
}

function xucli() {
    docker exec ${NETWORK}_xud_1 xucli "$@"
}

alias help="xucli help"
alias addcurrency="xucli addcurrency"
alias addpair="xucli addpair"
alias ban="xucli ban"
alias getbalance="xucli getbalance"
alias connect="xucli connect"
alias create="xucli create"
alias discovernodes="xucli discovernodes"
alias executeswap="xucli executeswap"
alias getinfo="xucli getinfo"
alias getnodeinfo="xucli getnodeinfo"
alias listorders="xucli listorders"
alias listpairs="xucli listpairs"
alias listpeers="xucli listpeers"
alias openchannel="xucli openchannel"
alias orderbook="xucli orderbook"
alias removecurrency="xucli removecurrency"
alias removeorder="xucli removeorder"
alias removepair="xucli removepair"
alias shutdown="xucli shutdown"
alias unban="xucli unban"
alias unlock="xucli unlock"
alias buy="xucli buy"
alias sell="xucli sell"
