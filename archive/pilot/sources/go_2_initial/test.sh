#!/bin/sh
set -eu
RUN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export GOTOOLCHAIN=local
export GOCACHE={ORIGINAL_BENCHMARK_ROOT}/toolchains/go/cache
{ORIGINAL_BENCHMARK_ROOT}/toolchains/go/go/bin/go build -o "$RUN_DIR/local_tests" "$RUN_DIR/main.go" "$RUN_DIR/local_tests.go"
exec "$RUN_DIR/local_tests"
