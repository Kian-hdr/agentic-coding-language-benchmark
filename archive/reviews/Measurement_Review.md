# Measurement review: sustained workers and fair runtime comparisons

26 October 2026. This is a proposed measurement protocol plus bounded macOS/Zero feasibility checks, not another coding-agent benchmark or a claim of comparative performance.

## Decision

Use two explicitly different comparisons:

1. **All-nine batch throughput and resource baseline:** one already-built application process consumes a regular NDJSON file and emits one JSON response per input line. This is feasible for published Zero 0.3.4 through chunked regular-file reads. Include input parsing, computation and output encoding. Measure elapsed time, user/system CPU, memory and exact correctness/count, separately from compilation and startup.
2. **Persistent request/response latency subset:** only candidates demonstrated to support a genuine long-running request/response transport. Do not give Zero a fresh process per request and label it persistent. Missing transport support for a particular pinned backend is a capability finding, not proof the whole language is incapable of networking or streaming.

A bulk-file test cannot produce defensible per-request p95/p99 by dividing batch time or treating stdout line-arrival time as the execution time of each request. It can produce batch-throughput distributions and batch-completion latency percentiles across independent runs, with those labels.

## What Zero 0.3.4 actually supports here

Installed release: `{ORIGINAL_BENCHMARK_ROOT}/toolchains/zero/bin/zero`, 0.3.4 build 5b3a90a, native macOS ARM64 direct backend.

Evidence is stronger than a failed documentation search:

- Its bundled `zero skills get language` explicitly says there is no stdin and directs hosted programs to `std.args` and `std.fs`.
- `zero skills get stdlib --topic std.io` exposes span/buffer operations and line scanning, not a stdin reader.
- `std.fs.readBytesAt(path, offset, buffer)` was compiled and executed with a seven-byte buffer over a multi-line file; output matched the entire input exactly, including lines split across chunks.
- `std.fs.openOrRaise` + `std.fs.readOrRaise` appears in the bundled API signatures, but an otherwise accepted graph using it fails native compilation with BLD004 `IR_VALUE_FS_OPEN`. Documented signatures therefore do not establish support in this backend.
- The pinned native runtime implementation of `readBytesAt` opens the file, verifies it is a regular file, seeks to the offset, fills the buffer, closes the file, and returns TOTAL FILE SIZE rather than bytes read. Thus it can stream a large regular file in bounded memory but repeats open/fstat/seek/close per chunk. It is not O(N²) rereading of all preceding bytes.
- Passing a pipe through `/dev/stdin` to that path produced no output. Source confirms regular-file enforcement. This is not a supported substitute for stdin.

Probe artifacts: `toolchains/zero/deep_io_probe/{project,program,input.ndjson}`. The seven-byte probe is transport-only echo, not benchmark business logic. `open_project` preserves the documented-but-not-native-buildable file-handle attempt.

Source references: [bundled-language source](https://github.com/vercel-labs/zerolang/blob/v0.3.4/skill-data/language.md), [pinned runtime](https://github.com/vercel-labs/zerolang/blob/v0.3.4/native/zero-c/runtime/zero_runtime.c), [pinned file helpers](https://github.com/vercel-labs/zerolang/blob/v0.3.4/std/fs.0), [line helpers](https://github.com/vercel-labs/zerolang/blob/v0.3.4/std/io.0). The installed binary's version-matched output is authoritative if the first source path changes.

For the all-nine file protocol, use identical immutable NDJSON bytes, maximum line size and response semantics. Each candidate must do actual per-line parsing and task logic in its own language. A bounded chunk reader must preserve incomplete lines across chunks; `nextLine` accepts an unterminated span tail, so do not mistake every chunk tail for a complete request. Handle final line without LF, CRLF policy, empty-file behavior and overlong lines explicitly. Zero's fixed locals have a 128 KiB per-function limit; for example use a 16 KiB read chunk plus a 32 KiB carry/request buffer with a declared 32 KiB maximum line shared by all candidates. Include a boundary correctness fixture before timing. Seven bytes was a stress probe, not a sensible throughput chunk size.

## Build and process boundaries

Freeze source and hashes before timing. Compile release/optimized artifacts ahead of time; record exact flags and compiler versions. Suggested entry points are native binaries for Rust/Go/Swift/MoonBit/Zero, compiled JS under Node for TypeScript, the Python interpreter and source, a JVM and precompiled JAR for Kotlin, and BAML's packaged artifact. Do not use `cargo run`, `moon run`, `zero run`, on-demand swiftc, or BAML's compilation launcher in a runtime-only score.

Have shell wrappers `exec` the application so the measured PID becomes the actual application. Include all runtime threads; a JVM's GC/JIT is part of its runtime. Verify the process tree rather than assuming launchers do not fork. Prefer an explicit no-worker-subprocess rule for this single-process comparison. If application subprocesses are necessary, record their topology and use tree-aware accounting as below.

Keep **clean build**, **incremental build**, **cold application launch/first response**, and **warm sustained operation** in separate columns. A warmed filesystem cache is not a cold-boot test; do not purge OS caches or change system security/settings. For persistent workers, establish a ready handshake and exclude readiness/startup from steady-state latency while still reporting it separately.

## CPU: correct attribution on Darwin

For process-lifetime totals, record `ru_utime + ru_stime` using per-PID `wait4` collection in an isolated supervisor, or `/usr/bin/time -l` around the direct application. Avoid global `resource.getrusage(RUSAGE_CHILDREN)` before/after deltas while other workers are being launched/reaped by the same harness: their CPU contaminates the delta. Never use wall seconds as CPU seconds. Parallel threads can consume more CPU seconds than elapsed wall seconds.

`Popen.wait()`/`poll()` can reap a process before a separate `os.wait4()` call; do not have two reapers compete. Either the supervisor owns child creation and wait4, or use an isolated external timing process. Python documents wait4's PID/status/rusage result. Darwin's resource implementation aggregates reaped descendant usage into parents, but detached/unreaped children and still-live children are not automatically a complete process-tree measurement. Require children to finish/reap before parent completion, or collect each independently without double-counting already-aggregated descendants.

For a **measured warm window**, wait4's whole-lifetime CPU includes warmup. Prefer sampling cumulative live CPU at the two window boundaries using Darwin `proc_pid_rusage` and differencing user/system counters; include all application threads. Its structure is defined in current XNU headers and the local libproc call succeeded in this environment. Bind the exact installed SDK ABI/version and check return codes; fields have platform-specific units. `ri_user_time`/`ri_system_time` use nanoseconds, while `getrusage` exposes seconds/timeval through Python. Do not reinterpret Mach absolute-time fields as nanoseconds without conversion.

For a process tree, add each live PID's OWN deltas once and separately account for terminated descendants; do not sum parent `ri_child_*` totals and those same child totals. PID reuse and children exiting between polls can lose attribution. The simplest defensible pilot is a direct single application process with threads and no subprocesses. If only lifetime CPU is collected, label it lifetime CPU, not steady-state CPU.

Report user seconds, system seconds, total CPU seconds, completed correct requests, CPU microseconds per correct request, and total CPU including failures. A low cost obtained by returning early/wrong answers is not a performance win. Runtime CPU is not electrical energy or provider billing; do not infer battery consumption, joules or cloud savings from it alone.

## Memory: bytes and scope matter

The installed macOS `man 2 getrusage` explicitly states `ru_maxrss` is **bytes**. Divide by 1,048,576 for MiB, not by 1,024. Linux often uses KiB; make the OS conversion explicit. Apple's old online 1993 archived page says kilobytes and conflicts with the current local manual; use the current host documentation and XNU source assigning resident-size-max. The source also shows `ruadd` retains the maximum RSS, not the sum of concurrent processes.

Therefore `wait4.ru_maxrss` is a useful process-lifetime high-water mark, not a simultaneously summed tree footprint and not an isolated warm-window peak. Do not subtract pre/post high-water values to estimate a window peak.

For warm-window memory, poll current per-process resident bytes (e.g. `proc_pid_rusage.ri_resident_size`) at a declared cadence, such as 10 ms, and report **sampled peak RSS**, baseline idle RSS, end RSS and sample count. Sampling may miss short peaks. Physical footprint is a separate Darwin metric; do not relabel `ri_phys_footprint` as RSS. If summing process RSS, label aggregate RSS and note shared mappings may be double-counted. Report the harness separately; do not charge only some languages for the measurement controller.

## Sustained latency/load protocol

The following counts are proposed design choices, not universal statistical guarantees:

- Use at least five independent application launches per candidate/workload/load condition. Preserve every run, not only the fastest.
- Apply identical fixed warmup work and a predeclared minimum duration, e.g. 2,000 requests and five seconds. Log windowed performance to reveal ongoing JIT/GC stabilization; if warmup does not stabilize within a bounded cap, flag it rather than silently trimming until attractive. Use a disjoint warmup input sequence with the same workload shape.
- For request percentiles target at least 10,000 measured requests per run: only about 100 observations lie above empirical p99 before accounting for serial dependence. Tiny samples do not justify stable tail rankings. Report N, duration, quantile estimator (e.g. nearest rank), per-run p50/p95/p99 and variability across launches. Avoid six-digit precision on microbenchmarks whose instrument overhead is similar to the operation.
- For sequential request/response, start a monotonic `perf_counter_ns` timestamp just before the request write and stop after a complete response line is received. Explicitly flush responses. This measures end-to-end IPC/encoding latency at concurrency one, not isolated function time or server latency under independent arrivals.
- To measure overload/queueing, use a separately labeled open-loop arrival schedule. Timestamp intended arrival, actual send and response; include scheduling/queue delay and report offered rate, achieved rate, errors and backlog. A closed-loop client slows when the worker slows and can hide latency under intended load (coordinated omission). Do not mix these distributions. The wrk2 primary documentation explains this distinction for HTTP; the methodological point applies to queued worker traffic.
- Randomize workload input order with a fixed recorded seed and randomize language order within repeated blocks. Use paired identical request streams. Do not run languages concurrently when comparing their CPU/runtime on one laptop. Record hardware, OS, power state and disruptive background load; do not change power/security settings to chase wins.
- For batch-file comparison, warm file-cache conditions consistently, rotate file/repetition order and report repeated batch completion time, requests/s, bytes/s and resource totals. Do not call total/N a p95 or p99. If using a same-process warmup prefix, report CPU window snapshots or label lifetime totals; a timing marker/control protocol must be equally implemented and excluded from business logic metrics.

Primary references: [Python monotonic/performance clocks](https://docs.python.org/3/library/time.html#time.perf_counter_ns), [wrk2 methodology](https://github.com/giltene/wrk2), [Python wait4](https://docs.python.org/3/library/os.html#os.wait4), [XNU resource structures](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/resource.h), [XNU resource accounting](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_resource.c). The proposed sample counts and experimental blocking are this review's recommendations, not attributed to those APIs.

## Avoiding pipe deadlocks and instrumentation artifacts

Never write an entire large input pipe while leaving stdout/stderr undrained. A child can fill stdout and block while the parent blocks writing stdin. For finite batch input, Python `communicate()` handles simultaneous pipes but buffers output in controller memory; for large/persistent workloads use concurrent readers or an event loop, bounded queues and incremental NDJSON validation. Redirect diagnostics to a file or drain stderr independently; do not mix it into response stdout. EOF before the expected response count, extra outputs, malformed JSON, timeouts and nonzero exit codes are failures.

Keep pipe buffering and newline/framing policy equivalent. A text line reader can wait forever if a candidate omits LF; enforce a per-request timeout. Flush promptly for interactive latency; allow equally declared batching for throughput mode. Avoid huge controller-side output captures that become the peak-memory result. Validate outside the hot path where feasible, but always count and hash responses and then check correctness. Measure an echo/no-op transport separately to reveal harness overhead; do not subtract a noisy baseline and call the remainder exact application time.

On timeout start the worker in its own session/process group, send termination to that group, then kill if needed and reap it. Do not use unsafe threaded `preexec_fn` hooks merely to call setsid. Python documents pipe deadlocks and recommends communicate; `start_new_session` is the supported session option. A subprocess timeout does not establish that arbitrary grandchildren were stopped. [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html)

## Separate model efficiency and support from runtime scores

Report total input/output tokens, documented cached-input fields, retries, tool calls, task success and authoring time for matched GPT-6.1 Sol runs. Count language documentation and repair interactions. Cached tokens are generally a subset of input accounting, so do not add them again without provider semantics. Report attempted tasks and failed attempts, not only successful survivors. No currency estimate without verified applicable pricing; no claim that shorter syntax alone lowers end-to-end cost.

Compiler type probes, held-out functional cases, mutation/error handling, regressions and sustained correct responses address distinct reliability dimensions. Strong support evidence includes current maintainers, release history, supported targets, governance, licensing and actual commercial commitments. None is a numerical probability of survival. Preserve these dimensions in a decision table rather than collapsing them into a single invented score.
