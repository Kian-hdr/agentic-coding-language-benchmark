#!/bin/sh
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
request=$(cat -- "$1")
exec {ORIGINAL_BENCHMARK_ROOT}/toolchains/zero/bin/zero run "$here" -- "$request"
