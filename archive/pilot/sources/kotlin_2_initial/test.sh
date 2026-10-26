#!/bin/sh
set -eu
RUN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$RUN_DIR"
JAVA_HOME={ORIGINAL_HOMEBREW}/opt/openjdk@21 {ORIGINAL_BENCHMARK_ROOT}/toolchains/kotlin/kotlinc/bin/kotlinc Main.kt Tests.kt -jvm-target 21 -classpath {ORIGINAL_BENCHMARK_ROOT}/toolchains/kotlin/json-20260814.jar -include-runtime -d tests.jar
{ORIGINAL_HOMEBREW}/opt/openjdk@21/bin/java -cp "$RUN_DIR/tests.jar:{ORIGINAL_BENCHMARK_ROOT}/toolchains/kotlin/json-20260814.jar" TestsKt
