# Rust evaluation setup

Verified 26 October 2026. Existing toolchains were checked at ordinary Cargo/Homebrew/local locations and through command discovery; none was found. Installed official stable Rust **1.99.1** (`58cf8f9c3`, 2026-10-13), Cargo **1.99.1** (`5f94df478`, 2026-08-27), target `aarch64-apple-darwin` under this evaluation only. The official rustup shell bootstrap was saved and inspected. Installation used `--no-modify-path --profile minimal --default-toolchain 1.99.1`, with local RUSTUP_HOME and CARGO_HOME. No global shell edits.

Root: `{ORIGINAL_BENCHMARK_ROOT}/toolchains/rust`.

Environment: `RUSTUP_HOME=<root>/rustup`, `CARGO_HOME=<root>/cargo`, prepend `<root>/cargo/bin` to PATH. `<root>/template` is an edition-2024 Cargo project and verified JSON echo starter. Build from project directory with `cargo build --offline --locked`; binary `target/debug/agent_benchmark` takes one raw JSON command-line argument. Hello/JSON compilation and execution succeeded.

## Dependency exception

Rust stdlib does not include a JSON parser. To avoid burdening Rust with a handwritten parser while other languages have built-in JSON, this setup prefetches and vendors **serde_json = 1.0.154**, limited to protocol serialization and deserialization. Cargo.lock pins transitive versions; vendor source replacement allows offline builds. No algorithm/application dependency is authorized by this exception. Report it alongside results. Vendored/locked graph also includes serde 1.0.229, serde_core 1.0.229, serde_derive 1.0.229, itoa 1.0.18, memchr 2.8.3, zmij 1.0.23, proc-macro2 1.0.107, quote 1.0.47, syn 3.0.9 and unicode-ident 1.0.27 (not all are compiled for the basic Value-only use).

Neutral coding instructions: `packets/rust.md`. No agent performance run was performed by setup worker.

## Support and migration risk

Rust is an established, general-purpose systems language with a public compiler, standard library, Cargo and community governance. The independent nonprofit Rust Foundation supports the project; its board includes project representation and several corporate members, with equal collective voting power between member/project director groups. Foundation membership is evidence of institutional support, not a promise of future funding or special GPT performance.

Stable releases use a six-week train. Official documentation says only the latest stable version is supported; maintaining security updates is ongoing work, rather than pinning forever. Stable-language compatibility and edition migration mechanisms are stronger continuity signals than a pre-1.0 language's aspirations. Compiler/runtime sources are primarily MIT/Apache-2.0, with third-party notices, enabling independent maintenance subject to their terms. This sharply reduces single-vendor lock-in but does not make migration away from Rust free: ownership/lifetimes, traits and crate usage still need rewriting. Existing TypeScript/Python UI or data ecosystems are not automatically replaced by Rust.

Primary sources:
- https://rustup.rs/
- https://static.rust-lang.org/dist/channel-rust-stable.toml (snapshot retained locally)
- https://doc.rust-lang.org/book/appendix-07-nightly-rust.html
- https://rustfoundation.org/about/
- https://github.com/rust-lang/rust/blob/main/COPYRIGHT
- https://docs.rs/serde_json/1.0.154/serde_json/
