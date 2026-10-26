#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export MOON_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/moonbit
export PATH="$MOON_HOME/bin:$PATH"
moon -C "$ROOT/solution" build --quiet --target native >&2
REQUEST=$(cat -- "$1")
exec "$ROOT/solution/_build/native/debug/build/cmd/main/main.exe" "$REQUEST"
