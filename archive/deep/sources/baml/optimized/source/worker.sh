#!/bin/sh
set -eu
dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export BAML_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/baml
export DO_NOT_TRACK=1
exec "$dir/worker" --input "$1" --output "$2" >/dev/null
