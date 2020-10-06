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
                    echo >&2 "Missing option value: $OPTION"
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

URL="https://raw.githubusercontent.com/ExchangeUnion/xud-docker/$BRANCH/setup.sh"

if ! command -v curl >/dev/null; then
    echo >&2 "Command \"curl\" not found"
    exit 1
fi

if SCRIPT=$(curl -s "$URL"); then
    if [[ "$SCRIPT" == "404: Not Found" ]]; then
        echo >&2 "Xud-docker branch \"$BRANCH\" does not exist"
        exit 1
    fi
    bash -c "$SCRIPT" -- "$@"
else
    EXIT_CODE="$?"
    case "$EXIT_CODE" in
    6)
        echo >&2 "Couldn't resolve host: raw.githubusercontent.com (please check your Internet connection and https://githubstatus.com)"
        exit 1
        ;;
    7)
        echo >&2 "Failed to connect to host: raw.githubusercontent.com (please check your Internet connection and https://githubstatus.com)"
        exit 1
        ;;
    *)
        echo >&2 "Failed to fetch setup.sh for branch \"$BRANCH\" (curl exits with $EXIT_CODE)"
        exit 1
        ;;
    esac
fi
