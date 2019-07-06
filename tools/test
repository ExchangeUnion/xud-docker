#!/bin/bash

set -euo pipefail

__dir__=`cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd`

platform=${1:-ubuntu-18}

cd tests/$platform

vagrant destroy -f
vagrant up

$__dir__/xud.exp
