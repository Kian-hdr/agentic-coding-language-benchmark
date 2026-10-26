#!/bin/sh
set -eu
BASE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export JAVA_HOME={ORIGINAL_HOMEBREW}/opt/openjdk@21
exec {ORIGINAL_BENCHMARK_ROOT}/toolchains/kotlin/kotlinc/bin/kotlinc \
    "$BASE/Main.kt" -jvm-target 21 \
    -classpath {ORIGINAL_BENCHMARK_ROOT}/toolchains/kotlin/json-20260814.jar \
    -include-runtime -d "$BASE/app.jar"
