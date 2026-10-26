#!/bin/sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export RUSTUP_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/rust/rustup
export CARGO_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/rust/cargo
export PATH="$CARGO_HOME/bin:$PATH"
cd "$SCRIPT_DIR"
exec cargo build --release --offline --locked
