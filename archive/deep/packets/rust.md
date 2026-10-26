The authoritative task is SPEC.md. The OLD packet below describes compiler paths/syntax only; ignore its old single-request run.sh / argument protocol. Implement new build.sh and one persistent worker.sh INPUT_JSONL OUTPUT_JSONL. All task computation and file parsing/serialization in assigned language.

# Rust benchmark implementation packet

Use stable Rust 1.99.1. Implement the supplied task, not just the sample.

Set these for commands:

```sh
export RUSTUP_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/rust/rustup
export CARGO_HOME={ORIGINAL_BENCHMARK_ROOT}/toolchains/rust/cargo
export PATH="$CARGO_HOME/bin:$PATH"
```

The starter is `{ORIGINAL_BENCHMARK_ROOT}/toolchains/rust/template`. Copy its `Cargo.toml`, `Cargo.lock`, `.cargo`, `vendor`, and `src` into your assigned directory; exclude its target directory. Replace echo logic with the requested implementation. `serde_json = "=1.0.154"` and locked transitive crates are pre-vendored solely for JSON protocol support. No additional third-party application dependencies. This declared infrastructure exception avoids writing a JSON parser for the benchmark.

Run `cargo build --offline --locked` from your project. Create executable `run.sh` that accepts one request-file path, reads the JSON, and passes the content as a single argument to `target/debug/agent_benchmark`. It must print exactly one JSON result on stdout, diagnostics on stderr, and work from any caller directory. The runner can compile when necessary.

Verified JSON pattern:

```rust
let text = std::env::args().nth(1).expect("JSON argument");
let request: serde_json::Value = serde_json::from_str(&text).expect("valid JSON");
// Compute the result here.
println!("{}", serde_json::to_string(&request).expect("serializable JSON"));
```

Use `Value::as_array`, `as_object`, `as_str`, `as_i64`, `as_u64`, `as_f64` to inspect inputs and `serde_json::json!` to construct outputs. Choose numeric types deliberately. Standard `Vec`, `HashMap`, `HashSet`, `BTreeMap`, iterators, sorting and string methods are available. Rust ownership prevents invalid aliasing, but borrowed values must not outlive owners. Prefer straightforward owned structs/collections over complex lifetime designs for small tasks. `cargo check --offline --locked` checks types, and `cargo test --offline --locked` runs tests. Do not add features or nightly requirements.

Primary docs: https://doc.rust-lang.org/book/ and https://docs.rs/serde_json/1.0.154/serde_json/.

Prefer symlinking pre-vendored template/vendor into your project instead of copying it. Build --release --offline --locked. Worker uses BufRead.lines and BufWriter, not raw request argv.
