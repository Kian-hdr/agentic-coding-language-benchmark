#!/bin/sh
set -eu
BASE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec {ORIGINAL_HOMEBREW}/opt/openjdk@21/bin/java \
    -cp "$BASE/app.jar:{ORIGINAL_BENCHMARK_ROOT}/toolchains/kotlin/json-20260814.jar" \
    MainKt "$@"
