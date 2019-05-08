#!/bin/bash

# fail fast
set -e
# set -x

docker-compose build
docker-compose up -d

function btcctl() {
    docker-compose exec btcd btcctl --simnet --rpcuser=xu --rpcpass=xu $@
} 

function ltcctl() {
    docker-compose exec ltcd ltcctl --simnet --rpcuser=xu --rpcpass=xu $@
} 

function lncli1() {
    docker-compose exec lndbtc1 lncli -n simnet -c bitcoin $@
}

function lncli2() {
    docker-compose exec lndbtc2 lncli -n simnet -c bitcoin $@
}

function lncli3() {
    docker-compose exec lndltc1 lncli -n simnet -c litecoin $@
}

function lncli4() {
    docker-compose exec lndltc2 lncli -n simnet -c litecoin $@
}

function xucli1() {
    docker-compose exec xud1 xucli $@
}

function xucli2() {
    docker-compose exec xud2 xucli $@
}

sleep 10

echo "Generate initial 100 blocks to get 50 BTC (extra 197 blocks to enable segwit maybe)"
# generate 100 blocks trigger lnd error TX rejected: transaction xxx has witness data, but segwit isn't active yet
btcctl --wallet generate 297

echo "Generate initial 100 blocks to get 50 LTC (extra 197 blocks to enable segwit maybe)"
# generate 100 blocks trigger lnd error TX rejected: transaction xxx has witness data, but segwit isn't active yet
ltcctl --wallet generate 297

echo "btcwallet balance:"
btcctl --wallet getbalance

echo "ltcwallet balance:"
ltcctl --wallet getbalance

# p2wkh/np2wkh
lnaddr1="$(lncli1 newaddress p2wkh | awk -F ':|\\r' '{print $2}' | sed 's/"//g')"
lnaddr2="$(lncli2 newaddress p2wkh | awk -F ':|\\r' '{print $2}' | sed 's/"//g')"
lnaddr3="$(lncli3 newaddress p2wkh | awk -F ':|\\r' '{print $2}' | sed 's/"//g')"
lnaddr4="$(lncli4 newaddress p2wkh | awk -F ':|\\r' '{print $2}' | sed 's/"//g')"

echo "lndbtc1 deposit address: $lnaddr1"
echo "lndbtc2 deposit address: $lnaddr2"
echo "lndltc1 deposit address: $lnaddr3"
echo "lndltc2 deposit address: $lnaddr4"

echo "Unlock btcwallet for 10 minutes"
btcctl --wallet walletpassphrase "xu" 600
echo "Transfer 1 BTC from btcwallet to lndbtc1"
btcctl --wallet sendfrom default $lnaddr1 1
echo "Confirm that transfer"
btcctl --wallet generate 1
echo "Transfer 1 BTC from btcwallet to lndbtc2"
btcctl --wallet sendfrom default $lnaddr2 1
echo "Confirm that transfer"
btcctl --wallet generate 1

echo "Unlock ltcwallet for 10 minutes"
ltcctl --wallet walletpassphrase "xu" 600
echo "Transfer 1 LTC from ltcwallet to lndltc1"
ltcctl --wallet sendfrom default "$lnaddr3" 1
echo "Confirm that transfer"
ltcctl --wallet generate 1
echo "Transfer 1 LTC from ltcwallet to lndltc2"
ltcctl --wallet sendfrom default "$lnaddr4" 1
echo "Confirm that transfer"
ltcctl --wallet generate 1

# Check balance for lndbtc1, lndbtc2, lndltc1, lndltc2
lncli1 walletbalance
lncli2 walletbalance
lncli3 walletbalance
lncli4 walletbalance

# Get lndbtc2, lndltc2 node identity_pubkey
lnkey2="$(lncli2 getinfo | grep pubkey | awk -F ':|,' '{print $2}' | tr -d '"')"
lnkey4="$(lncli4 getinfo | grep pubkey | awk -F ':|,' '{print $2}' | tr -d '"')"

echo $lnkey2
echo $lnkey4

echo "Connect lndbtc1 to lndbtc2"
lncli1 connect $lnkey2@lndbtc2
echo "Connect lndltc1 to lndltc2"
lncli3 connect $lnkey4@lndltc2

echo "List lndbtc1 connected peers"
lncli1 listpeers
echo "List lndltc1 connected peers"
lncli3 listpeers

echo "Open channel from lndbtc1 to lndbtc2 with 0.1 BTC (=1e7 satoshi)"
lncli1 openchannel $lnkey2 10000000
echo "Open channel from lndltc1 to lndltc2 with 0.1 LTC (=1e7 satoshi)"
lncli3 openchannel $lnkey4 10000000

# Generate 3 extra blocks to confirm the channels created above
echo "Confirm the BTC payment channel"
btcctl --wallet generate 3
echo "Confirm the LTC payment channel"
ltcctl --wallet generate 3

# See balance of lnd node
lncli1 walletbalance
lncli1 channelbalance

lncli3 walletbalance
lncli3 channelbalance

# Place order in xud
# xucli1 buy 0.01 LTC/BTC 0.013
# xucli1 listorders
