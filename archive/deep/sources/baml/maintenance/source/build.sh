#!/bin/sh
set -eu
dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export BAML_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/baml
export DO_NOT_TRACK=1
exec "$BAML_HOME/bin/baml" --agent-skill-check off --directory "$dir" pack main --output "$dir/worker"
