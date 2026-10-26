#!/bin/sh
set -eu
exec {ORIGINAL_HOMEBREW}/bin/node "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/dist/worker.js" "$@"
