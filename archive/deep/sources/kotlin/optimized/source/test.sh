#!/bin/sh
set -eu
BASE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export JAVA_HOME={ORIGINAL_HOMEBREW}/opt/openjdk@21
JSON={ORIGINAL_BENCHMARK_ROOT}/toolchains/kotlin/json-20260814.jar
{ORIGINAL_BENCHMARK_ROOT}/toolchains/kotlin/kotlinc/bin/kotlinc \
    "$BASE/Tests.kt" -jvm-target 21 -classpath "$BASE/app.jar:$JSON" -d "$BASE/tests.jar"
exec "$JAVA_HOME/bin/java" -cp "$BASE/tests.jar:$BASE/app.jar:$JSON" TestsKt "$BASE"
