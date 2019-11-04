if [[ -z ${XUD_NETWORK:-} ]]; then
    echo >&2 "Missing XUD_NETWORK"
    exit 1
fi

if [[ -z ${XUD_DOCKER_HOME:-} ]]; then
    echo >&2 "Missing XUD_DOCKER_HOME"
    exit 1
fi

if [[ -z ${XUD_NETWORK_DIR:-} ]]; then
    echo >&2 "Missing XUD_NETWORK_DIR"
    exit 1
fi

export XUD_NETWORK
export XUD_DOCKER_HOME
export XUD_NETWORK_DIR

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
    grep -A 999 services docker-compose.yml | sed -nE 's/^  ([a-z]+):$/\1/p' | sort | paste -sd " " -
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

function report() {
    log_details
    echo "Please click on https://github.com/ExchangeUnion/xud/issues/new?assignees=kilrau&labels=bug&template=bug-report.md&title=Short%2C+concise+description+of+the+bug, describe your issue, drag and drop the file \"xud-docker.log\" which is located in $XUD_NETWORK_DIR into your browser window and submit your issue."
}

cat "$XUD_DOCKER_HOME/banner.txt"

alias status="bash $XUD_DOCKER_HOME/status.sh"
alias status2="bash $XUD_DOCKER_HOME/status2.sh"

function check_simnet_channels() {
    # This function originates from the xud-simnet-channels script
    local needBTC needLTC server head connectstr

    needBTC=1
    if ! lndbtc-lncli getinfo | grep '"num_active_channels": 0,' >/dev/null 2>&1; then
        echo "active BTC channel found"
        needBTC=0
    fi
    if ! lndbtc-lncli getinfo | grep '"num_pending_channels": 0,' >/dev/null 2>&1; then
        echo "pending BTC channel found"
        needBTC=2
    fi
    needLTC=1
    if ! lndltc-lncli getinfo | grep '"num_active_channels": 0,' >/dev/null 2>&1; then
        echo "active LTC channel found"
        needLTC=0
    fi
    if ! lndltc-lncli getinfo | grep '"num_pending_channels": 0,' >/dev/null 2>&1; then
        echo "pending LTC channel found"
        needLTC=2
    fi
    if [ "$needBTC" = 0 ] && [ "$needLTC" = 0 ]; then
        exit 1
    fi
    # ensure connection to test nodes
    xucli connect 02b66438730d1fcdf4a4ae5d3d73e847a272f160fee2938e132b52cab0a0d9cfc6@35.196.118.79:8885 >/dev/null 2>&1
    xucli connect 028599d05b18c0c3f8028915a17d603416f7276c822b6b2d20e71a3502bd0f9e0a@35.231.171.148:8885 >/dev/null 2>&1
    xucli connect 03fd337659e99e628d0487e4f87acf93e353db06f754dccc402f2de1b857a319d0@35.229.81.83:8885 >/dev/null 2>&1
    sleep 5

    if [ "$needBTC" = 1 ]; then
        echo "Opening BTC channel"
        let server="$RANDOM % 3 +1"
        let head="$server*2"
        connectstr=$(xucli -j listpeers | egrep -A1 '"BTC"|address' | sed -n '1p;7p;13p;5p;11p;17p' | head -n $head | tail -n 2 | sed 's/\"//g' | sed 's/\,//' | sed 's/ //g' | tac | paste -d "@" - - | sed 's/address://' | cut -d ":" -f1)
        echo "open channel with $connectstr"
        lndbtc-lncli connect $connectstr:10012
    fi

    if [ "$needLTC" = 1 ]; then
        echo "Opening LTC channel"
        let server="$RANDOM % 3 +1"
        let head="$server*2"
        connectstr=$(xucli -j listpeers | egrep -A1 '"LTC"|address' | sed -n '1p;7p;13p;5p;11p;17p' | head -n $head | tail -n 2 | sed 's/\"//g' | sed 's/\,//' | sed 's/ //g' | tac | paste -d "@" - - | sed 's/address://' | cut -d ":" -f1)
        echo "open channel with $connectstr"
        lndltc-lncli connect $connectstr:10011
    fi

    echo "waiting for BTC channel to be active"
    while true; do
        echo -n "."
        if lndbtc-lncli listchannels 2>&1 | grep active >/dev/null 2>&1; then
            break
        fi
        sleep 1
    done
    echo -e "\nBTC channel is active"

    echo "waiting for LTC channel to be active"
    while true; do
        echo -n "."
        if lndltc-lncli listchannels 2>&1 | grep active >/dev/null 2>&1; then
            break
        fi
        sleep 1
    done
    echo -e "\nLTC channel is active"
}

if [[ $XUD_NETWORK == "simnet" ]]; then
    check_simnet_channels
fi
