#!/bin/sh
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export MOON_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/moonbit
export PATH="$MOON_HOME/bin:$PATH"
exec "$MOON_HOME/bin/moon" -C "$PROJECT_DIR" build --frozen --target native --release
