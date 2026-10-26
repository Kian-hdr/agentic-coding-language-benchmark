#!/bin/sh
set -eu
RUN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export GOTOOLCHAIN=local
export GOCACHE={ORIGINAL_BENCHMARK_ROOT}/toolchains/go/cache
if [ ! -x "$RUN_DIR/program" ] || [ "$RUN_DIR/main.go" -nt "$RUN_DIR/program" ]; then
 {ORIGINAL_BENCHMARK_ROOT}/toolchains/go/go/bin/go build -o "$RUN_DIR/program" "$RUN_DIR/main.go"
fi
exec "$RUN_DIR/program" "$(cat -- "$1")"
