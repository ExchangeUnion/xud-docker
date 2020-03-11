# xud-docker

[![Discord](https://img.shields.io/discord/547402601885466658.svg)](https://discord.gg/YgDhMSn)
[![Docker Pulls](https://img.shields.io/docker/pulls/exchangeunion/xud)](https://hub.docker.com/r/exchangeunion/xud)

A complete [xud](https://github.com/ExchangeUnion/xud) environment using [docker](https://www.docker.com/). Get started trading using xud-docker 👉 [here](https://docs.exchangeunion.com/start-trading/user-guide) 👈

## Developing

The following instructions are geared towards developers, intending to contribute to xud-docker.

### Initial setup

```bash
git clone https://github.com/ExchangeUnion/xud-docker.git $PROJECT_DIR
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
# Auto-detect changed images and build them
tools/build
# Build a specific image 
tools/build <image>:<tag>
# Build multiple images
tools/build <image1>:<tag> <image2>:<tag>
tools/build <image>:<tag1> <image>:<tag2>
```

Test locally

```bash
./xud.sh -b your-feature-branch
```

In case you modified utils image, you could test locally like

```bash
./xud.sh -b your-feature-branch --dev
```

The option `--dev` means using local built utils image.

To let others test without building the images by themselves push the images of your-feature-branch.

```bash
# Auto-detect changed images and push them
tools/push
# Push a specific image
tools/push <image>:<tag>
# Push multiple images
tools/push <image1>:<tag> <image2>:<tag>
tools/push <image>:<tag1> <image>:<tag2>
```

Then push your local changes to remote branch

```bash
git push origin your-feature-branch
```

Ask other people to run your-feature-branch on their machine

```bash
./xud.sh -b your-feature-branch
```
