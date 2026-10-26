# Sustained application-worker specification

Implement in the assigned language, using the installed pinned toolchain.
Provide executable build.sh and worker.sh. build.sh builds an optimized/release
artifact. worker.sh INPUT_JSONL OUTPUT_JSONL runs that prebuilt artifact exactly
once, processing the whole file in one process. No build during worker.sh.
Each nonblank input line is one independent JSON request; write one JSON response
line in the same order. Read incrementally where the platform permits. Support
LF, CRLF, and a final unterminated line. All business logic, parsing, processing
and output serialization must be in the assigned language. Host shell wrappers
may launch/map arguments only. No helper process per request. Diagnostics stderr.
No stdout requirement; evaluator reads OUTPUT_JSONL. All data is synthetic.

Use exact integer arithmetic. Inputs/intermediates/results remain within
[-2^53+1,2^53-1], but often exceed 32-bit. JSON numeric fields must be numbers,
not quoted decimal strings. All customer/route/status identifiers are ASCII.
Lexicographical order means ASCII alphabetical order, not length-first order.
Individual input lines may be 100 KiB; files may contain hundreds of lines.
Invalid JSON must produce {"error":"invalid_json"} and continue to later lines.
Unknown op produces {"error":"unknown_op"}. Other requests have the stated schema.
Requests are independent: processing A, B, A must return identical A results.

## invoice

Input {"op":"invoice","events":[{"id":"e1","customer":" A ",
"amount_cents":150,"status":"paid"}]}.
Process in input order. First occurrence of each event id wins, even if invalid;
later occurrences count as duplicates and are skipped before further checks.
Trim ASCII whitespace (space, tab, LF, CR, VT, FF) from customer.
Reject an event if customer is empty, amount_cents is negative, or status is not
paid/refund/pending/void. Count it as rejected, without contributing a customer.
Valid pending/void events are ignored. Valid paid/refund events are accepted.
Group accepted events by normalized customer; retain zero-net customers.
Output customer rows sorted lexicographically, each with customer, gross_cents,
refund_cents, net_cents=gross-refund, count=accepted events for that customer.
Output also accepted, duplicates, ignored, rejected and overall gross_cents,
refund_cents, net_cents. Empty events produces empty customers and zero counts.
Example response for the input above:
{"customers":[{"customer":"A","gross_cents":150,"refund_cents":0,
"net_cents":150,"count":1}],"accepted":1,"duplicates":0,"ignored":0,
"rejected":0,"gross_cents":150,"refund_cents":0,"net_cents":150}.

## access_log

Input {"op":"access_log","start_ms":100,"end_ms":200,"events":[
{"ts_ms":120,"route":" /api/orders ","status":503,"duration_us":1234,"bytes":20}]}.
Only include events start_ms <= ts_ms < end_ms. All fields have valid types;
durations/bytes are nonnegative. Normalize route with ASCII whitespace trimming.
Group included events by route. Each route row: route, count, errors (status>=500),
total_bytes, max_us and p95_us. p95 is sorted duration at index ceil(95*n/100)-1.
Output routes sorted lexicographically and total_count, total_errors, total_bytes.
Example {"routes":[{"route":"/api/orders","count":1,"errors":1,
"total_bytes":20,"max_us":1234,"p95_us":1234}],"total_count":1,
"total_errors":1,"total_bytes":20}. Empty selection yields routes=[] and zeros.

## telemetry

Input {"op":"telemetry","samples":[-2,5,8,1],"window":2,"threshold":3}.
For each full trailing window, compute integer average with division truncating
toward zero. Let these averages be a[0..m-1]. Output count=m, min, max,
above=count of a[i]>threshold, and weighted_checksum=sum((i+1)*a[i]).
If window<=0 or window>number of samples, return {"error":"invalid_window"}.
For the example averages=[1,6,4], output
{"count":3,"min":1,"max":6,"above":2,"weighted_checksum":25}.
This represents rolling sensor analytics. Choose a scalable algorithm; output
does not include the full moving-average series.

## Dependencies and preparation

Standard libraries plus preregistered JSON support only. Rust serde_json and
Kotlin org.json are already staged. Official MoonBit async is allowed for IO and
already staged as a transport-only starter. No new downloads in timed runs.
Pure Python is the initial baseline. A separately disclosed NumPy implementation
may be used in the optimization stage if supplied by the parent beforehand.
Any size caps or unsupported behavior must be reported, not silently hidden.
Build all dependency paths so worker.sh works from a different current directory.
