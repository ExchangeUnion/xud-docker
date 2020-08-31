# xud-docker

[![Discord](https://img.shields.io/discord/547402601885466658.svg)](https://discord.gg/YgDhMSn)
[![Docker Pulls](https://img.shields.io/docker/pulls/exchangeunion/xud)](https://hub.docker.com/r/exchangeunion/xud)

A complete [xud](https://github.com/ExchangeUnion/xud) environment targeted at market makers using [docker](https://www.docker.com/). Follow the 👉 [market maker guide](https://docs.exchangeunion.com/start-earning/market-maker-guide) 👈

## Developing

The following instructions are geared towards developers, intending to contribute to xud-docker.

### Prerequisites

Python 3.8 (or higher)

### Initial setup

```bash
git clone https://github.com/ExchangeUnion/xud-docker.git $PROJECT_DIR
```

### Developing a feature

Create a feature branch.

```
git checkout -b your-feature-branch
```

Make your desired changes to the images located at: `$PROJECT_DIR/images`.

Build your modified images.

```bash
tools/build
```

Test it locally.

```bash
bash setup.sh -b your-feature-branch
```

To let others test without building the images by themselves push your feature branch to remote repository. Travis will build & push images for you.

```bash
git push origin your-feature-branch
```

After the corresponding Travis build succeeded, other people can easily run your feature branch on their machine like this.

```bash
bash xud.sh -b your-feature-branch
```


## Use local built images

You could run xud-docker with your local built images.

```bash
git clone https://github.com/ExchangeUnion/xud-docker.git
cd xud-docker
git checkout -b local
```

#### Example: Use simnet (light mode)

```
tools/build utils xud lndbtc-simnet lndltc-simnet connext
bash setup.sh -b local --dev --use-local-images xud,lndbtc,lndltc,connext
```

#### Example: Use testnet (light mode)

```
tools/build utils xud lndbtc lndltc connext
bash setup.sh -b local --dev --use-local-images xud,lndbtc,lndltc,connext
```

#### Example: Use mainnet (light mode)

See `images/utils/config/template.py` to get the right version of mainnet images

```
tools/build utils xud:1.0.0-rc.2 lndbtc:0.11.0-beta lndltc:0.11.0-beta.rc1 connext:1.3.1
bash setup.sh -b local --dev --use-local-images xud,lndbtc,lndltc,connext
```

#### Example: Enable optional service arby

Enabling boltz and webui works in a same way. 

1. Build arby image `tools/build arby`
2. Append arby to --use-local-images
3. Append `--arby.disabled=false` or persist below in your network conf file.

```
[arby]
disabled = false
```
