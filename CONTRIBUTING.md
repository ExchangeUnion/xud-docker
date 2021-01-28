## Contribute to the Xud-Docker Project

The following instructions are geared towards developers, intending to contribute to xud-docker.

### Prerequisites

Golang 1.15 (or higher)

### Initial setup

```sh
git clone https://github.com/ExchangeUnion/xud-docker.git
```

### Developing a feature

Create a feature branch.

```sh
git checkout -b your-feature
```

Make your desired changes to the images or launcher.

Build your modified images.

```sh
tools/build <image>:<tag>
```

Build the launcher

```sh
cd launcher
make
```

Run your branch with modified images locally

```sh
./launcher setup
```

To let others test without building the images by themselves push your feature branch to remote repository. Travis will build & push images for you.

```sh
git push origin your-feature
```

After the corresponding GitHub actions build succeeded, other people can easily run your feature branch on their machine like this.

```sh
BRANCH=your-feature xud-launcher setup
```

The xud-launcher binary is from [here](https://github.com/ExchangeUnion/xud-launcher/releases).
