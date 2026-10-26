# Zero operations

Run `./run.sh REQUEST_FILE`. The shell wrapper transports the JSON request to Zero;
all parsing, calculations, graph processing, grouping, sorting, and response
serialization are implemented in `zero.graph`. Readable projections are in `src/`.

Run `./tests.sh` for 25 end-to-end cases. Example requests are preserved in
`test_calc.json`, `test_ledger.json`, and `test_topo.json`.

Toolchain limitation: the installed native backend rejects PageAlloc locals and
World parameters on helpers. This implementation therefore uses fixed buffers:
65,536 response bytes, 60,000 bytes for decoded escaped strings, and 65,536 nodes.
Large inputs exceeding these buffers are not supported. The request also passes
through argv and is subject to the operating system's argument size limit.
