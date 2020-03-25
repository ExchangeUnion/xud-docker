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

Create a feature branch.

```
git checkout -b your-feature-branch
```

Make your desired changes to the images located at: `$PROJECT_DIR/images`.

Build your modified images. Optionally modify the `nodes.json` in the project root if necessary.

```bash
tools/build
```

Test it locally.

```bash
./xud.sh -b your-feature-branch
```

or

```bash
./xud.sh -b your-feature-branch --nodes-json ./nodes.json
```

To let others test without building the images by themselves push your feature branch to remote repository. Travis will build & push images for you.

```bash
git push origin your-feature-branch
```

After corresponding Travis build turned green ask other people to run your feature branch on their machine.

```bash
./xud.sh -b your-feature-branch
```
