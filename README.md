xud-docker
==========


This project comprises a containerized [xud](https://github.com/ExchangeUnion/xud) environment for easy
* development with regtest (producing blocks locally)
* playing on our simnet (private chains maintained by our cloud instances, automatic channel management and allocation of coins, trading bots) Status: live
* real-world playing (testnet) Status: in development
* and reckless trading (mainnet) Status: in development

### Requirements

docker-ce 18.09 or higher with current user added to docker group. Check [the official install instructions.](https://docs.docker.com/install/)


### How to run

```bash
mkdir my-xud
cd my-xud
curl https://raw.githubusercontent.com/exchangeunion/xud-docker/master/xud-simnet/docker-compose.dist.yml > docker-compose.yml
docker-compose up -d

# Apply the aliases: btcctl, ltcctl, lndbtc-lncli, lndltc-lncli, xucli
alias btcctl="docker-compose exec btcd btcctl --simnet --rpcuser=xu --rpcpass=xu"
alias ltcctl="docker-compose exec ltcd ltcctl --simnet --rpcuser=xu --rpcpass=xu"
alias lndbtc-lncli="docker-compose exec lndbtc lncli -n simnet -c bitcoin"
alias lndltc-lncli="docker-compose exec lndltc lncli -n simnet -c litecoin"
alias xucli="docker-compose exec xud xucli"
alias logs="docker-compose logs"

# Inspect instance logs
docker-compose logs -f btcd/ltcd/lndbtc/lndltc/xud

# Shutdown the xud environment
docker-compose down
```

### References

* [BTCD config options](https://godoc.org/github.com/btcsuite/btcd)
* [LTCD config options](https://godoc.org/github.com/ltcsuite/ltcd)
* [LND config options](https://github.com/lightningnetwork/lnd/blob/master/sample-lnd.conf)
* [XUD config options](https://github.com/ExchangeUnion/xud/blob/master/sample-xud.conf)
