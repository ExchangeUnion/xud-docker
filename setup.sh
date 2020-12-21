#!/usr/bin/env bash

set -euo pipefail

case $(uname) in
Linux)
    HOME_DIR="$HOME/.xud-docker"
    ;;
Darwin)
    HOME_DIR="$HOME/Library/Application Support/XudDocker"
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
    "https://github.com/ExchangeUnion/xud-launcher/releases/latest/download/linux-amd64.zip"
fi

./xud-launcher "$@"
