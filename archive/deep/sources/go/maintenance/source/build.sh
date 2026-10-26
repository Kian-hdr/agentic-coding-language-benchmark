#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"
export GOTOOLCHAIN=local
# Keep compiler writes inside the assigned workspace.
export GOCACHE="$ROOT/.go_cache"
exec {ORIGINAL_BENCHMARK_ROOT}/toolchains/go/go/bin/go build -trimpath -ldflags='-s -w' -o "$ROOT/program" main.go
