xud-docker
==========

[![Build Status](https://travis-ci.org/ExchangeUnion/xud-docker.svg?branch=master)](https://travis-ci.org/ExchangeUnion/xud-docker)

This project comprises a 0-install, containerized [xud](https://github.com/ExchangeUnion/xud) environment for
* development with **regtest** (producing blocks locally)
Status: **in development**
* playing on our **simnet** (private chains maintained by exchange union cloud instances, automatic channel management and allocation of coins, trading against bots)
Status: **live**
* real-world playing on **testnet**
Status: **in development**
* reckless trading on **mainnet**
Status: **in development**



### Requirements

1. Linux, macOS or [Windows with WSL 2](https://devblogs.microsoft.com/commandline/wsl-2-is-now-available-in-windows-insiders/).

2. docker >= 18.09
```
$ docker --version
Docker version 18.09.6, build 481bc77
```
3. docker-compose >= 1.24
```
$ docker-compose --version
docker-compose version 1.24.0, build 0aa59064
```
4. current user can run docker without sudo
```
$ docker run hello-world
```
If this doesn't work, [check here](https://docs.docker.com/install/linux/linux-postinstall/). If you don't have docker installed yet, follow [the official install instructions.](https://docs.docker.com/install/)



### How to run

Start the environment with
```bash
curl https://raw.githubusercontent.com/ExchangeUnion/xud-docker/master/xud.sh -o ~/xud.sh
bash ~/xud.sh 
```
This guides you through a setup on first run, pulls necessary containers, syncs chains and gets you into `xud ctl` when all is up and ready. `xud ctl` takes [`xucli` commands](https://api.exchangeunion.com) and some more, like `status` to check on the underlying clients like `bitcoind`, `litecoind` or `geth`. Once the `xud` environment is setup and ready, `xud ctl` is 

Permanently set xud alias to launch `xud ctl` from anywhere:
```bash
source ~/.bashrc
```

To inspect logs
```bash
#Simnet
docker-compose logs -f btcd/ltcd/lndbtc/lndltc/xud
```

Shutdown th environment and remove containers
```bash
docker-compose down
```

### References
Simnet only:
* [btcd config options](https://godoc.org/github.com/btcsuite/btcd)
* [ltcd config options](https://godoc.org/github.com/ltcsuite/ltcd)

All others:
* [bitcoind config options](https://github.com/bitcoin/bitcoin/blob/master/share/examples/bitcoin.conf)
* [litecoind config options](https://litecoin.info/index.php/Litecoin.conf#litecoin.conf_Configuration_File)
* [geth config options](https://github.com/ethereum/go-ethereum/blob/master/README.md)
* [lnd config options](https://github.com/lightningnetwork/lnd/blob/master/sample-lnd.conf)
* [raiden config options](https://raiden-network.readthedocs.io/en/stable/config_file.html)
* [xud config options](https://github.com/ExchangeUnion/xud/blob/master/sample-xud.conf)
