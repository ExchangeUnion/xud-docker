DOCKER_COMPOSE="docker-compose -p $XUD_NETWORK"

case $XUD_NETWORK in
    mainnet)
        alias bitcoin-cli="$DOCKER_COMPOSE exec bitcoind bitcoin-cli -rpcuser=xu -rpcpassword=xu"
        alias litecoin-cli="$DOCKER_COMPOSE exec litecoind litecoin-cli -rpcuser=xu -rpcpassword=xu"
        alias lndbtc-lncli="$DOCKER_COMPOSE exec lndbtc lncli -n mainnet -c bitcoin"
        alias lndltc-lncli="$DOCKER_COMPOSE exec lndltc lncli -n mainnet -c litecoin"
        alias geth="$DOCKER_COMPOSE exec geth geth"
        ;;
    testnet)
        alias bitcoin-cli="$DOCKER_COMPOSE exec bitcoind bitcoin-cli -testnet -rpcuser=xu -rpcpassword=xu"
        alias litecoin-cli="$DOCKER_COMPOSE exec litecoind litecoin-cli -testnet -rpcuser=xu -rpcpassword=xu"
        alias lndbtc-lncli="$DOCKER_COMPOSE exec lndbtc lncli -n testnet -c bitcoin"
        alias lndltc-lncli="$DOCKER_COMPOSE exec lndltc lncli -n testnet -c litecoin"
        alias geth="$DOCKER_COMPOSE exec geth geth --testnet"
        ;;
    simnet)
        alias btcctl="$DOCKER_COMPOSE exec btcd btcctl --simnet --rpcuser=xu --rpcpass=xu"
        alias ltcctl="$DOCKER_COMPOSE exec ltcd ltcctl --simnet --rpcuser=xu --rpcpass=xu"
        alias lndbtc-lncli="$DOCKER_COMPOSE exec lndbtc lncli -n simnet -c bitcoin"
        alias lndltc-lncli="$DOCKER_COMPOSE exec lndltc lncli -n simnet -c litecoin"
        ;;
esac

GRACEFUL_SHUTDOWN_TIMEOUT=180

alias logs="$DOCKER_COMPOSE logs"
alias start="$DOCKER_COMPOSE start"
alias stop="$DOCKER_COMPOSE stop -t $GRACEFUL_SHUTDOWN_TIMEOUT"
alias restart="$DOCKER_COMPOSE restart -t $GRACEFUL_SHUTDOWN_TIMEOUT"
alias up="$DOCKER_COMPOSE up"
alias down="$DOCKER_COMPOSE down -t $GRACEFUL_SHUTDOWN_TIMEOUT"

function xucli() {
    LINE=""
    #shellcheck disable=SC2068
    docker-compose exec xud xucli $@ | while read -n 1; do
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
            fi
        fi
    done
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

export PS1="$XUD_NETWORK > "

function get_all_services() {
    cat docker-compose.yml | grep -A 999 services | sed -nE 's/^  ([a-z]+):$/\1/p' | sort | paste -sd " " -
}

function log_details() {
    logfile="$XUD_NETWORK_DIR/xud-docker.log"
    commands=(
        "uname -a"
        "docker info"
        "docker stats --no-stream"
        "docker-compose ps"
    )
    services=$(get_all_services)
    for s in $services; do
        commands+=("$DOCKER_COMPOSE logs --tail=1000 $s")
    done

    set +e
    for cmd in "${commands[@]}"; do
        echo $cmd >> $logfile
        eval $cmd >> $logfile 2>&1
        echo "" >> $logfile
    done
    set -e
}

report() {
    log_details
    echo "Please click on https://github.com/ExchangeUnion/xud/issues/new?assignees=kilrau&labels=bug&template=bug-report.md&title=Short%2C+concise+description+of+the+bug, describe your issue, drag and drop the file \"xud-docker.log\" which is located in $HOME/.xud-docker into your browser window and submit your issue."
}

enter() {
    docker run --rm -it --entrypoint bash $1
}

cat $XUD_DOCKER_HOME/banner.txt

alias status="bash $XUD_DOCKER_HOME/status.sh"

PYTHON="python3"
if ! command -v $PYTHON >/dev/null 2>&1; then
    PYTHON="python"
fi

alias status2="$PYTHON $XUD_DOCKER_HOME/status.py status"

$PYTHON $XUD_DOCKER_HOME/status.py check
