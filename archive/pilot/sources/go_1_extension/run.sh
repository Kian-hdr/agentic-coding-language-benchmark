#!/bin/sh
set -eu
RUN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REQUEST=$(cat -- "$1")
export GOTOOLCHAIN=local
export GOCACHE={ORIGINAL_BENCHMARK_ROOT}/toolchains/go/cache
GO={ORIGINAL_BENCHMARK_ROOT}/toolchains/go/go/bin/go
if [ ! -x "$RUN_DIR/program" ] || [ "$RUN_DIR/main.go" -nt "$RUN_DIR/program" ] || [ "$RUN_DIR/go.mod" -nt "$RUN_DIR/program" ]; then
 cd "$RUN_DIR"
 "$GO" build -o "$RUN_DIR/program" "$RUN_DIR/main.go"
fi
exec "$RUN_DIR/program" "$REQUEST"
