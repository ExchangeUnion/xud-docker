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

temp_file=$(mktemp)
HTTPCODE=$(curl -Ls -w "%{http_code}" -o temp_file "https://raw.githubusercontent.com/ExchangeUnion/xud-docker/$BRANCH/setup.sh" || 
           echo >&2 "Timeout error: Couldn't connect to GitHub: please check your internet connection and githubstatus.com")
if [ $HTTPCODE -eq 404 ]; then
    echo >&2 "❌ Branch \"$BRANCH\" does not exist"
elif [ $HTTPCODE -ne 200 ]; then
    echo >&2 "Something went wrong: got "$HTTPCODE" response code from GitHub. Please check githubstatus.com"
else
    bash temp_file "$@"
    rm ${temp_file} && exit 0
fi
exit 1
