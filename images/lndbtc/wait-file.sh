#!/bin/bash
set -euo pipefail
set -m

wait_file() {
  local file="$1"; shift
  local wait_seconds="${1:-10}"; shift # timeout 10 seconds

  until test $((wait_seconds--)) -eq 0 -o -f "$file" ; do sleep 1; done

  ((++wait_seconds))
}

export -f wait_file
