xud-docker
==========

This project is trying to build a containerized [xud](https://github.com/ExchangeUnion/xud) environment for development and production.

### How to run

Start `xud` and its dependencies from scratch

```
./install.sh
```

Shutdown all instances and purge the data

```
./uninstall.sh
```

### Other topics

- Generate transactions & trasfer money
- Develop Xud
- Run exchange demos on Xud
- Set up proxies for go modules, npm modules and alpine repository

### Handy commands

```
docker-compose build --no-cache btcd

btcctl --simnet --rpcuser=xu --rpcpass=xu --wallet generate 1

https://gist.github.com/farukterzioglu/f5e270387f11a8dfd27b9077004ff32c
btcd --simnet --rpcuser=xu --rpcpass=xu
btcwallet --simnet --username=xu --password=xu --create
btcwallet --simnet --username=xu --password=xu
btcctl --simnet --rpcuser=xu --rpcpass=xu --wallet walletpassphrase "xu" 600
btcctl --simnet --rpcuser=xu --rpcpass=xu --wallet createnewaccount account1
btcctl --simnet --rpcuser=xu --rpcpass=xu --wallet listaccounts
btcctl --simnet --rpcuser=xu --rpcpass=xu --wallet getnewaddress
btcd --simnet --rpcuser=xu --rpcpass=xu --miningaddr=SQqiiJtfueX54oFGuTAzkBTaM23neFvWNF

docker-compose run btcwallet --create

alias btcctl="docker-compose exec btcd btcctl --simnet --rpcuser=xu --rpcpass=xu"
alias ltcctl="docker-compose exec ltcd ltcctl --simnet --rpcuser=xu --rpcpass=xu"
alias lncli="docker-compose exec lndbtc1 lncli --no-macaroons"
alias xucli="docker-compose exec xud1 xucli"

btcctl getinfo
btcctl --wallet listaccounts
btcctl --wallet generate 1

# First 50 coins need to generate 100 blocks
btcctl --wallet getblance

lncli getinfo

xucli getinfo
```


### References

* [Btcd options](https://godoc.org/github.com/btcsuite/btcd)
* [Ltcd options](https://godoc.org/github.com/ltcsuite/ltcd)
* [Lnd options](https://github.com/lightningnetwork/lnd/blob/master/sample-lnd.conf)
* [Xud options](https://github.com/ExchangeUnion/xud/blob/master/sample-xud.conf)
