#!/bin/bash

set -euo pipefail
shopt -s expand_aliases

install_raiden() {
    pushd ~/xud-simnet/raiden-wd > /dev/null
    source venv/bin/activate
    pip install -c ../raiden/constraints.txt -r ../raiden/requirements.txt ../raiden
    popd > /dev/null
}

install_raiden

#cat /tmp/xud-simnet-install.log