#!/bin/bash

set -x

source xud-simnet/setup.bash

xud-simnet-install

cd ~/xud-simnet/xud

npm run compile


xud-simnet-start