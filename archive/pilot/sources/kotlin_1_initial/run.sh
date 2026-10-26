#!/bin/sh
set -eu
RUN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec {ORIGINAL_HOMEBREW}/opt/openjdk@21/bin/java -cp "$RUN_DIR/app.jar:{ORIGINAL_BENCHMARK_ROOT}/toolchains/kotlin/json-20260814.jar" MainKt "$1"
