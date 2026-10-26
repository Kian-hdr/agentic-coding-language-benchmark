# Zero operations

Run `./run.sh REQUEST_FILE`. The shell wrapper only reads the request and
launches the installed Zero toolchain. All JSON handling, ledger processing,
topological ordering, expression evaluation, and response formatting are in
`src/lib.0` and `src/main.0`, with `zero.graph` as the compiler input.

Run `./tests.sh` for 36 end-to-end checks. The three `test_*.json` example files
are also retained. `test_request.json` is the test harness's current request.

Implementation uses caller-owned buffers because the installed native backend
cannot lower heap allocator locals. Current capacities are 130,000 response
bytes; 24,000 bytes per ledger decoded-string/scratch buffer; 40,000 bytes per
topological string buffer and 40,000 nodes; 130,000 expression bytes; and
16,384 calculator values / 32,768 operators. Requests also use the operating
system's argument-length limit. Inputs exceeding these capacities are not
fully supported; SPEC.md does not specify size bounds.
