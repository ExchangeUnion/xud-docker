[![Discord](https://img.shields.io/discord/547402601885466658.svg)](https://discord.gg/YgDhMSn)
[![Docker Pulls](https://img.shields.io/docker/pulls/exchangeunion/xud)](https://hub.docker.com/r/exchangeunion/xud)

xud-docker
==========
A complete [xud](https://github.com/ExchangeUnion/xud) environment using [docker](https://www.docker.com/).

Get started trading 👉 [here](https://docs.exchangeunion.com/start-trading/user-guide) 👈

## Developing
The following chapter is meant for developers.

### Initial setup

```bash
git clone https://github.com/ExchangeUnion/xud-docker.git $PROJECT_DIR
```

Init and fetch git submodules

```bash
cd $PROJECT_DIR
git submodule init
git submodule update --recursive --remote
```

### Developing a feature

Create a feature branch

```
git checkout -b your-feature-branch
```

Make your desired changes to the images located at:
`~/xud-docker/images`

Build the updated image(s)

```bash
$PROJECT_DIR/tools/build <image_name>
```

Test locally

```bash
$PROJECT_DIR/xud.sh -b your-feature-branch
```

To let others test without building the images by themselves push the images of your-feature-branch.

```bash
$PROJECT_DIR/tools/push <image_name>
```

Then push your local changes to remote branch

```bash
git push origin your-feature-branch
```

Ask other people to run your-feature-branch on their machine

```bash
./xud.sh -b your-feature-branch
```

### Test on cloud

Running simnet, testnet and mainnet simultaneously is resource heavy. We provide a convenient `tools/test` script to test your-feature-branch in the cloud. Currently, only Google Cloud is supported.

1. Download `google-cloud-sdk` on your machine.
2. Run `gcloud init` to login to your Google account and choose the project and region

```
$PROJECT_DIR/tools/test --on-cloud <network>
```

The value of `<network>` should be simnet, testnet and mainnet

