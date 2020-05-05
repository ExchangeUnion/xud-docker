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

                HTTPCODE=$(curl -ILs -w "%{http_code}" -o /dev/null https://api.github.com/repos/ExchangeUnion/xud-docker/git/refs/heads/$1)
                if [ $HTTPCODE -eq 404 ]; then
                    echo >&2 "❌ Branch \"$1\" does not exist"
                    exit 1
                elif [ $HTTPCODE -eq 000 ]; then
                    echo >&2 "Timeout error: Couldn't connect to GitHub: please check your internet connection and githubstatus.com"
                    exit 1
                elif [ $HTTPCODE -ne 200 ]; then
                    echo >&2 "Something went wrong: got "$HTTPCODE" response code from GitHub. Please check githubstatus.com"
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
