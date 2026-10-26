#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export RUSTUP_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/rust/rustup
export CARGO_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/rust/cargo
export PATH="$CARGO_HOME/bin:$PATH"
REQUEST=$(cat -- "$1")
cd "$ROOT"
if [ ! -x target/debug/agent_benchmark ] || [ src/main.rs -nt target/debug/agent_benchmark ]; then
    cargo build --offline --locked >&2
fi
exec "$ROOT/target/debug/agent_benchmark" "$REQUEST"
