#!/bin/sh
set -eu
dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export BAML_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/baml
export DO_NOT_TRACK=1
"$BAML_HOME/bin/baml" --agent-skill-check off --directory "$dir" test
for name in calc ledger topo unknown; do
    "$dir/run.sh" "$dir/tests/${name}_example.json" > "$dir/tests/${name}_example.actual.json"
    cmp "$dir/tests/${name}_example.expected.json" "$dir/tests/${name}_example.actual.json"
done
cd "$dir/tests"
../run.sh calc_example.json > calc_relative.actual.json
cmp calc_example.expected.json calc_relative.actual.json
