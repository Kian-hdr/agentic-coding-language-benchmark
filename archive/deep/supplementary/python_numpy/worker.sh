#!/bin/sh
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec {ORIGINAL_BENCHMARK_ROOT}/deep_phase/toolchains/python/bin/python -O "$script_dir/worker.pyc" "$@"
