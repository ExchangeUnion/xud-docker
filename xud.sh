#!/bin/bash

set -euo pipefail

BRANCH=master

function parse_arguments() {
    local OPTION VALUE
    while [[ $# -gt 0 ]]; do
        case $1 in
        "-b" | "--branch")
            if [[ $1 =~ = ]]; then
                VALUE=$(echo "$1" | cut -d'=' -f2)
            else
                OPTION=$1
                shift
                if [[ $# -eq 0 || $1 =~ ^- ]]; then
                    echo >&2 "❌ Missing option value: $OPTION"
                    exit 1
                fi
                if ! curl -sf -o /dev/null https://api.github.com/repos/ExchangeUnion/xud-docker/git/refs/heads/$1; then
                    echo >&2 "❌ Branch \"$1\" does not exist"
                    exit 1
                fi
                VALUE=$1
            fi
            BRANCH=$VALUE
            ;;
        *)
            shift
        esac
    done
}

parse_arguments "$@"

bash <(curl -sf "https://raw.githubusercontent.com/ExchangeUnion/xud-docker/$BRANCH/setup.sh") "$@"
