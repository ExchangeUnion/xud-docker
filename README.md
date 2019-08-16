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

