#!/bin/sh
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec {ORIGINAL_BENCHMARK_ROOT}/toolchains/zero/bin/zero build --profile release-fast --out "$here/program" "$here"
