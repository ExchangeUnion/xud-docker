xud-docker
==========

[![Build Status](https://travis-ci.org/ExchangeUnion/xud-docker.svg?branch=master)](https://travis-ci.org/ExchangeUnion/xud-docker)

This project comprises a 0-install containerized [xud](https://github.com/ExchangeUnion/xud) environment for
* development with **regtest** (producing blocks locally)
Status: **in development**
* playing on our **simnet** (private chains maintained by our cloud instances, automatic channel management and allocation of coins, trading against bots)
Status: **live**
* real-world playing on **testnet**
Status: **in development**
* reckless trading on **mainnet**
Status: **in development**

### Requirements

1. docker >= 18.09
```
$ docker --version
Docker version 18.09.6, build 481bc77
```
2. docker-compose >= 1.24
```
$ docker-compose --version
docker-compose version 1.24.0, build 0aa59064
```
3. current user can run docker without sudo
```
$ docker run hello-world
```
If not [check this](https://docs.docker.com/install/linux/linux-postinstall/).

If you do't have docker installed yet, follow [the official install instructions.](https://docs.docker.com/install/)


### How to run

```bash
curl https://raw.githubusercontent.com/ExchangeUnion/xud-docker/master/xud.sh -o ~/xud.sh
bash ~/xud.sh 
```

Set xud alias (works on linux & macOS)
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
Simnet:
* [BTCD config options](https://godoc.org/github.com/btcsuite/btcd)
* [LTCD config options](https://godoc.org/github.com/ltcsuite/ltcd)
All:
* [LND config options](https://github.com/lightningnetwork/lnd/blob/master/sample-lnd.conf)
* [XUD config options](https://github.com/ExchangeUnion/xud/blob/master/sample-xud.conf)
