#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export RUSTUP_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/rust/rustup
export CARGO_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/rust/cargo
export PATH="$CARGO_HOME/bin:$PATH"
if [ ! -x "$ROOT/target/debug/agent_benchmark" ] || [ "$ROOT/src/main.rs" -nt "$ROOT/target/debug/agent_benchmark" ]; then
    (cd "$ROOT" && cargo build --offline --locked >&2)
fi
exec "$ROOT/target/debug/agent_benchmark" "$(cat -- "$1")"
