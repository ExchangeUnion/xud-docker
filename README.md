xud-docker
==========

This project is trying to build a containerized [xud](https://github.com/ExchangeUnion/xud) environment for development and production.

### How to run

```bash
mkdir my-xud
cd my-xud
curl https://raw.githubusercontent.com/exchangeunion/xud-docker/master/xud-simnet-fast/docker-compose.dist.yml > docker-compose.yml
docker-compose up -d

# Apply the aliases: btcctl, ltcctl, lndbtc-lncli, lndltc-lncli, xucli
curl https://raw.githubusercontent.com/exchangeunion/xud-docker/master/xud-simnet-fast/aliases.bash | source

# Inspect instance logs
docker-compose logs -f btcd/ltcd/lndbtc/lndltc/xud

# Remove the xud environment
docker-compose down
```

### References

* [Btcd options](https://godoc.org/github.com/btcsuite/btcd)
* [Ltcd options](https://godoc.org/github.com/ltcsuite/ltcd)
* [Lnd options](https://github.com/lightningnetwork/lnd/blob/master/sample-lnd.conf)
* [Xud options](https://github.com/ExchangeUnion/xud/blob/master/sample-xud.conf)
