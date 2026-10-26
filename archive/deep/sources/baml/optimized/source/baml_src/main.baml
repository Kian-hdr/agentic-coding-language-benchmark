// Persistent application worker with bounded incremental file transport.
class InvoiceEvent {
    id: string,
    customer: string,
    amount_cents: int,
    status: string,
}

class InvoiceRequest {
    events: InvoiceEvent[],
}

class Customer {
    customer: string,
    gross_cents: int,
    refund_cents: int,
    net_cents: int,
    count: int,
}

class InvoiceResult {
    customers: Customer[],
    accepted: int,
    duplicates: int,
    ignored: int,
    rejected: int,
    gross_cents: int,
    refund_cents: int,
    net_cents: int,
}

class AccessEvent {
    ts_ms: int,
    route: string,
    status: int,
    duration_us: int,
    bytes: int,
}

class AccessRequest {
    start_ms: int,
    end_ms: int,
    events: AccessEvent[],
}

class RouteGroup {
    route: string,
    count: int,
    errors: int,
    total_bytes: int,
    durations: int[],
    max_us: int,
}

class RouteResult {
    route: string,
    count: int,
    errors: int,
    total_bytes: int,
    max_us: int,
    p95_us: int,
}

class AccessResult {
    routes: RouteResult[],
    total_count: int,
    total_errors: int,
    total_bytes: int,
}

class TelemetryRequest {
    samples: int[],
    window: int,
    threshold: int,
}

class TelemetryResult {
    count: int,
    min: int,
    max: int,
    above: int,
    weighted_checksum: int,
}

class ErrorResult {
    error: string,
}

function ascii_space(c: string?) -> bool {
    c == " " || c == "\t" || c == "\n" || c == "\r" || c == "\u000b" || c == "\u000c"
}

function trim_ascii(s: string) -> string {
    // Native Unicode trimming is identical on the specified ASCII identifiers.
    if (s.is_ascii()) {
        return s.trim();
    }
    let lo = 0;
    let hi = s.length();
    while (lo < hi && ascii_space(s.at(lo))) {
        lo += 1;
    }
    while (hi > lo && ascii_space(s.at(hi - 1))) {
        hi -= 1;
    }
    if (lo == 0 && hi == s.length()) {
        s
    } else {
        s.slice(lo, hi)
    }
}

function invoice(req: InvoiceRequest) -> InvoiceResult {
    let seen: map<string, bool> = {};
    let groups: map<string, Customer> = {};
    let result = InvoiceResult {
        customers: [],
        accepted: 0,
        duplicates: 0,
        ignored: 0,
        rejected: 0,
        gross_cents: 0,
        refund_cents: 0,
        net_cents: 0,
    };
    for (let event in req.events) {
        if (seen.has(event.id)) {
            result.duplicates += 1;
            continue;
        }
        seen.set(event.id, true);
        let name = trim_ascii(event.customer);
        if (
            name == ""
                || event.amount_cents < 0
                || !(
                    event.status == "paid"
                        || event.status == "refund"
                        || event.status == "pending"
                        || event.status == "void"
                )
        ) {
            result.rejected += 1;
            continue;
        }
        if (event.status == "pending" || event.status == "void") {
            result.ignored += 1;
            continue;
        }
        let group = if let existing: Customer = groups.get(name) {
            existing
        } else {
            let created = Customer { customer: name, gross_cents: 0, refund_cents: 0, net_cents: 0, count: 0 };
            groups.set(name, created);
            created
        };
        group.count += 1;
        result.accepted += 1;
        if (event.status == "paid") {
            group.gross_cents += event.amount_cents;
            result.gross_cents += event.amount_cents;
        } else {
            group.refund_cents += event.amount_cents;
            result.refund_cents += event.amount_cents;
        }
        group.net_cents = group.gross_cents - group.refund_cents;
    }
    result.customers
        = groups.values().sort_by((a, b) -> {
            a.customer.cmp(b.customer)
        });
    result.net_cents = result.gross_cents - result.refund_cents;
    result
}

// Three-way selection avoids sorting and handles repeated durations linearly.
function select_duration(values: int[], k: int) -> int {
    let lo = 0;
    let hi = values.length() - 1;
    let budget = values.length() * 8;
    while (lo < hi) {
        // Bound partition work even for adversarial pivot arrangements.
        budget -= hi - lo + 1;
        if (budget < 0) {
            let remaining = values.slice(lo, hi + 1);
            remaining.sort_by((a, b) -> {
                a.cmp(b)
            });
            return remaining[k - lo];
        }
        let a = values[lo];
        let b = values[(lo + hi) / 2];
        let c = values[hi];
        let pivot = if (a < b) {
            if (b < c) {
                b
            } else if (a < c) {
                c
            } else {
                a
            }
        } else {
            if (a < c) {
                a
            } else if (b < c) {
                c
            } else {
                b
            }
        };
        let left = lo;
        let i = lo;
        let right = hi;
        while (i <= right) {
            let value = values[i];
            if (value < pivot) {
                values[i] = values[left];
                values[left] = value;
                left += 1;
                i += 1;
            } else if (value > pivot) {
                values[i] = values[right];
                values[right] = value;
                right -= 1;
            } else {
                i += 1;
            }
        }
        if (k < left) {
            hi = left - 1;
        } else if (k > right) {
            lo = right + 1;
        } else {
            return pivot;
        }
    }
    values[k]
}

function access_log(req: AccessRequest) -> AccessResult {
    let groups: map<string, RouteGroup> = {};
    let result = AccessResult { routes: [], total_count: 0, total_errors: 0, total_bytes: 0 };
    for (let event in req.events) {
        if (event.ts_ms < req.start_ms || event.ts_ms >= req.end_ms) {
            continue;
        }
        let route = trim_ascii(event.route);
        let group = if let existing: RouteGroup = groups.get(route) {
            existing
        } else {
            let created = RouteGroup {
                route: route,
                count: 0,
                errors: 0,
                total_bytes: 0,
                durations: [],
                max_us: 0,
            };
            groups.set(route, created);
            created
        };
        group.count += 1;
        result.total_count += 1;
        if (event.status >= 500) {
            group.errors += 1;
            result.total_errors += 1;
        }
        group.total_bytes += event.bytes;
        result.total_bytes += event.bytes;
        group.durations.push(event.duration_us);
        if (event.duration_us > group.max_us) {
            group.max_us = event.duration_us;
        }
    }
    for (
        let group in groups.values().sort_by((a, b) -> {
            a.route.cmp(b.route)
        })
    ) {
        result.routes.push(
            RouteResult {
                route: group.route,
                count: group.count,
                errors: group.errors,
                total_bytes: group.total_bytes,
                max_us: group.max_us,
                p95_us: select_duration(group.durations, (95 * group.count + 99) / 100 - 1),
            },
        );
    }
    result
}

function telemetry(req: TelemetryRequest) -> TelemetryResult | ErrorResult {
    let n = req.samples.length();
    let w = req.window;
    if (w <= 0 || w > n) {
        return ErrorResult { error: "invalid_window" };
    }
    let sum = 0;
    let i = 0;
    while (i < w) {
        sum += req.samples[i];
        i += 1;
    }
    let first = sum / w;
    let result = TelemetryResult { count: n - w + 1, min: first, max: first, above: 0, weighted_checksum: 0 };
    i = w - 1;
    while (i < n) {
        if (i >= w) {
            sum -= req.samples[i - w];
            sum += req.samples[i];
        }
        let avg = sum / w;
        if (avg < result.min) {
            result.min = avg;
        }
        if (avg > result.max) {
            result.max = avg;
        }
        if (avg > req.threshold) {
            result.above += 1;
        }
        result.weighted_checksum += (i - w + 2) * avg;
        i += 1;
    }
    result
}

// Release the generic JSON tree before aggregating typed requests.
function parse_request(
    text: string,
) -> InvoiceRequest | AccessRequest | TelemetryRequest | ErrorResult {
    let value = baml.json.parse(text);
    let op = baml.json.field(value, "op");
    if (op == "invoice") {
        return baml.json.to<InvoiceRequest>(value);
    }
    if (op == "access_log") {
        return baml.json.to<AccessRequest>(value);
    }
    if (op == "telemetry") {
        return baml.json.to<TelemetryRequest>(value);
    }
    ErrorResult { error: "unknown_op" }
}

function process(text: string) -> string {
    let req = parse_request(text);
    if (req is InvoiceRequest) {
        return baml.json.stringify(invoice(req));
    }
    if (req is AccessRequest) {
        return baml.json.stringify(access_log(req));
    }
    if (req is TelemetryRequest) {
        return baml.json.stringify(telemetry(req));
    }
    baml.json.stringify(req)
}

function emit(raw: uint8array, output: baml.fs.File) -> void {
    let i = 0;
    while (i < raw.length()) {
        let c = raw[i];
        if (!(c == 32 || c == 9 || c == 10 || c == 13 || c == 11 || c == 12)) {
            break;
        }
        i += 1;
    }
    if (i == raw.length()) {
        return;
    }
    let response = process(string.from_utf8(raw)) catch (e) {
        baml.json.ParseError | baml.errors.InvalidArgument => {
            baml.json.stringify(ErrorResult { error: "invalid_json" })
        },
    };
    output.write(response + "\n");
}

function main(input: string, output: string) -> void {
    let reader = baml.fs.open(input, "r");
    defer { reader.close(); }
    let writer = baml.fs.open(output, "w");
    defer { writer.close(); }
    let pending = b"";
    while let chunk: uint8array = reader.read(65536) {
        pending
            = if (pending.length() == 0) {
                chunk
            } else {
                pending.concat(chunk)
            };
        while let newline: int = pending.index_of(10) {
            emit(pending.slice(0, newline), writer);
            pending = pending.slice(newline + 1, pending.length());
        }
    }
    if (pending.length() > 0) {
        emit(pending, writer);
    }
    writer.flush();
}
