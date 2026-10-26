#!/bin/sh
set -eu
MOON_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/moonbit
export MOON_HOME
PATH="$MOON_HOME/bin:$PATH"
export PATH
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
moon -C "$ROOT/solution" build --quiet --target native >&2
exec "$ROOT/solution/_build/native/debug/build/cmd/main/main.exe" "$(cat -- "$1")"
