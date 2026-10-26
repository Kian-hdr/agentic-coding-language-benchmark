# Independent deep-phase oracle review

Reviewed 26 October 2026: `deep_phase/SPEC.md`, `deep_phase/oracle.py`, and maintenance instructions in `deep_phase/agent_runs.py:40-49`. No benchmark implementation was executed or modified. Generator was not called; existing datasets and expected-output files were not changed. Cases below are evaluator-only evidence and must not be passed to benchmark coding agents.

**Conclusion: no reference-output correctness blocker found within the stated input schemas.** The requested semantic points match the specification. This is a bounded independent review, not a proof over all JSON or every future generator configuration.

## Verified semantics

- **Invoice first occurrence wins, including invalid first events:** `oracle.py:14-18` checks duplicates before all further checks and inserts a new ID into `seen` before validation. An invalid original cannot be replaced by a valid duplicate. Rejected events create no customer; ignored pending/void events create no customer. Customers with accepted events remain present at zero net. ASCII trimming uses the exact six whitespace characters required by SPEC; parsing the source confirms these are actual escaped control characters, not literal backslash-letter pairs.
- **Log p95:** `oracle.py:43` uses `(95*n+99)//100-1`, exactly `ceil(95*n/100)-1` for positive integer n. Groups always contain at least one duration, so no negative-index empty-group error occurs. Inclusion correctly uses the half-open time interval, and errors count all statuses at least 500. Sorted ASCII keys match the declared lexical order.
- **Signed division:** `oracle.py:46` divides the absolute numerator using integer division and restores its sign. Window validation guarantees a strictly positive divisor. It therefore truncates toward zero without float conversion. Sliding-window averaging and one-based weighted checksum agree with the example.
- **Maintenance fee condition:** `with_fee = maintenance and 'fee_bps' in req` intentionally distinguishes an absent field from zero. No fee fields appear when absent; zero includes them. Every accepted customer, including refund-only rows, receives a zero-initialized fee field when enabled. Only accepted paid events accrue rounded fees; refunds do not. Both customer and aggregate net values subtract fees. `fee_validation` is maintenance-only, so ignoring this future field during initial-stage reference generation is appropriate.

## Independent oracle-only checks performed

Executed assertions for an invalid first ID followed by a valid duplicate, a zero-net accepted customer, ignored events, p95 ranks for group sizes 1 through 1,000, positive/negative truncation cases, fee half-rounding, refund-only rows, absent fees and zero fees. All passed. These checks exercised only reference functions, never submitted business programs.

## Generator bounds and coverage limits

At the current performance size of 512 invoice/log entries per request and 4,096 telemetry samples, conservative bounds are safe: invoice gross/refunds at most 25.6 billion cents, enabled paid-event fee multiplication at most 50 billion before the 5,000 rounding term, log total bytes below 10.24 billion, and telemetry weighted checksum magnitude at most 839.066 billion (strict bound `100000*4096*4097/2 = 839065600000`). All are below `2^53-1`, as are simple accumulation intermediates. The explicit five-billion-cent invoice validates beyond-32-bit handling. Line framing correctly emits LF/CRLF and final unterminated lines, and blank lines produce no expected response.

Coverage should remain honestly bounded: 100 KiB maximum permitted lines and near-53-bit arithmetic limits are not directly established by these workloads. The negative invoice amount is explicit only in a duplicate that should be skipped; deterministic first-event negative rejection would strengthen future coverage. The first-invalid duplicate rule, exact window boundaries and p95 discontinuities are sound in the oracle but deserve deliberate held-out fixtures rather than relying on randomized occurrence. Do not amend a frozen evaluation silently: document any added fixtures and rerun equivalent eligible stages for every language.

The reference parser uses Python `json.loads`, which accepts nonstandard NaN/Infinity by default and permits top-level scalars; `solve` expects an object. Current generated requests avoid those forms, so this does not invalidate current expected results. If broad adversarial JSON recovery becomes a scored promise, define strict JSON and non-object-request behavior first and extend the oracle consistently.
