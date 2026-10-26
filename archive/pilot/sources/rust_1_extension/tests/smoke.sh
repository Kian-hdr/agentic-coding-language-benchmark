#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd /
for operation in calc ledger topo; do
    actual=$("$ROOT/run.sh" "$ROOT/tests/${operation}_request.json")
    expected=$(cat "$ROOT/tests/${operation}_expected.json")
    if [ "$actual" != "$expected" ]; then
        printf '%s\n' "Unexpected $operation result: $actual" >&2
        exit 1
    fi
done
printf '%s\n' 'All launcher smoke tests passed.'
