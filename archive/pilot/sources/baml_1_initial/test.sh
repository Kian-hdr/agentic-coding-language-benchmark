#!/bin/sh
set -eu
dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export BAML_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/baml
export DO_NOT_TRACK=1
"$BAML_HOME/bin/baml" --agent-skill-check off --directory "$dir" test
check() {
    actual=$("$dir/run.sh" "$dir/$1")
    if [ "$actual" != "$2" ]; then
        printf 'FAIL %s: %s\n' "$1" "$actual" >&2
        exit 1
    fi
    printf 'PASS %s\n' "$1"
}
check test_request.json '{"value":-6}'
check tests/ledger_request.json '{"accounts":[{"account":"A","balance":2,"count":1},{"account":"bank","balance":0,"count":2}],"accepted":3}'
check tests/topo_request.json '{"order":["a","b","c"]}'
check tests/unknown_request.json '{"error":"unknown_op"}'
check tests/empty_account_request.json '{"error":"empty_account"}'
check tests/cycle_request.json '{"error":"cycle"}'
check tests/syntax_request.json '{"error":"syntax"}'
check tests/division_request.json '{"error":"division_by_zero"}'
