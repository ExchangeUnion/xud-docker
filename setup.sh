#!/usr/bin/env bash

set -euo pipefail

case $(uname) in
Linux)
    HOME_DIR="$HOME/.xud-docker"
    PLATFORM=linux
    ;;
Darwin)
    HOME_DIR="$HOME/Library/Application Support/XudDocker"
    PLATFORM=darwin
    ;;
*)
    echo "Unsupported platform: $(uname)"
    exit 1
esac

if [[ ! -e $HOME_DIR ]]; then
    mkdir "$HOME_DIR"
fi

cd "$HOME_DIR"

if [[ ! -e "xud-launcher" ]]; then
    curl "https://github.com/ExchangeUnion/xud-launcher/releases/download/v2.0.0-alpha.2/$PLATFORM-amd64.zip"
    unzip "$PLATFORM-amd64.zip"
fi

if [[ ! -x "xud-launcher" ]]; then
    chmod u+x xud-launcher
fi

echo "BRANCH=$BRANCH"
./xud-launcher setup "$@"
