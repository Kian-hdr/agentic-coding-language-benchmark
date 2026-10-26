#!/bin/sh
set -eu
RUN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec {ORIGINAL_HOMEBREW}/bin/node "$RUN_DIR/dist/main.js" "$1"
