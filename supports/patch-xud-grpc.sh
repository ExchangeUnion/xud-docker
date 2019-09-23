#!/bin/bash

set -euo pipefail

cd ~/xud-simnet/xud

sed -Ei 's|gpr_log|/*gpr_log|g' node_modules/grpc/deps/grpc/src/core/lib/gpr/env_linux.cc
sed -Ei 's|used);|used);*/|g' node_modules/grpc/deps/grpc/src/core/lib/gpr/env_linux.cc
sed -Ei 's/static_library/static_library --grpc_alpine=true/g' node_modules/grpc/package.json
apk add --no-cache alpine-sdk
npm rebuild grpc --build-from-source
