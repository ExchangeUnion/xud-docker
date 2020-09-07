#!/bin/bash

export NETWORK=$1
bash run_utils_test.sh dump_nodes --xud.options='--foo bar' | jq