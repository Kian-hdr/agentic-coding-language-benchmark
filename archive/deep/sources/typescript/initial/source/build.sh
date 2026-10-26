#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
exec {ORIGINAL_BENCHMARK_ROOT}/toolchains/typescript/node_modules/.bin/tsc -p tsconfig.json
