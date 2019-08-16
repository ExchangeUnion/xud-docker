xud-docker
==========
A 0-install [xud](https://github.com/ExchangeUnion/xud) environment using [docker](https://www.docker.com/)

Description and usage:
* [xud wiki](https://github.com/ExchangeUnion/xud/wiki/Docker)

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

Push images of your-feature-branch and let others test without build images by themselves

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

Or they need to build images of your-feature-branch test like you do it locally.

### Test on cloud

We know running simnet, testnet and mainnet simultaneously on personal computer is nearly impossible. So we provide a convenient `tools/test` to let your test your-feature-branch on cloud (We only support Google Cloud for now)

1. Download `google-cloud-sdk` on your machine.
2. Running `gcloud init` to login to your Google account and choose the project and region

```
$PROJECT_DIR/tools/test --on-cloud <network>
```

The value of `<network>` should be simnet, testnet and mainnet

