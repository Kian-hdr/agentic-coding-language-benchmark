#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export MOON_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/moonbit
export PATH="$MOON_HOME/bin:$PATH"
moon -C "$ROOT/solution" check
moon -C "$ROOT/solution" test --target native
ACTUAL=$("$ROOT/run.sh" "$ROOT/example.json")
[ "$ACTUAL" = '{"value":-6}' ]
printf '%s\n' 'Runner example passed.'
