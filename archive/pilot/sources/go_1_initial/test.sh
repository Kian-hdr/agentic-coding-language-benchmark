#!/bin/sh
set -eu
RUN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$RUN_DIR"
export GOTOOLCHAIN=local
export GOCACHE={ORIGINAL_BENCHMARK_ROOT}/toolchains/go/cache
GO={ORIGINAL_BENCHMARK_ROOT}/toolchains/go/go/bin/go
"$GO" run main.go checks.go
"$GO" vet main.go
ACTUAL=$(./run.sh example_request.json)
[ "$ACTUAL" = '{"value":-6}' ]
printf '%s\n' 'Launcher example passed'
