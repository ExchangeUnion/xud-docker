xud-docker
==========

[![Build Status](https://travis-ci.org/ExchangeUnion/xud-docker.svg?branch=master)](https://travis-ci.org/ExchangeUnion/xud-docker)

This project comprises a containerized [xud](https://github.com/ExchangeUnion/xud) environment for easy
* development with **regtest** (producing blocks locally) Status: **live**
* playing on our **simnet** (private chains maintained by our cloud instances, automatic channel management and allocation of coins, trading against bots) Status: **live**
* real-world playing on **testnet** Status: **in development**
* and reckless trading on **mainnet** Status: **in development**

### Requirements

git & docker-ce 18.09 (or higher) with user added to docker group. Check [the official install instructions.](https://docs.docker.com/install/)


### How to run

```bash
git clone https://github.com/ExchangeUnion/xud-docker.git ~/xud-docker
cd ~/xud-docker/
```

Change into the sub-folder of the network you want to run
```bash
cd xud-regtest
cd xud-simnet
cd xud-testnet
cd xud-mainnet
```

Start the environment
```bash
docker-compose up -d
```

Permanently set aliases (works on linux & macOS)
```bash
echo "source ./aliases.bash" >> ~/.bashrc
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

* [BTCD config options](https://godoc.org/github.com/btcsuite/btcd)
* [LTCD config options](https://godoc.org/github.com/ltcsuite/ltcd)
* [LND config options](https://github.com/lightningnetwork/lnd/blob/master/sample-lnd.conf)
* [XUD config options](https://github.com/ExchangeUnion/xud/blob/master/sample-xud.conf)
