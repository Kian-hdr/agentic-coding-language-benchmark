"""Persistent JSONL application worker with NumPy telemetry arithmetic."""
import json
import sys
import numpy as np

ASCII_WHITESPACE = " \t\n\r\v\f"
VALID_STATUSES = frozenset(("paid", "refund", "pending", "void"))


def invoice(request):
    include_fees = "fee_bps" in request
    fee_bps = request.get("fee_bps", 0)
    seen = set()
    customers = {}
    duplicates = ignored = rejected = 0
    for event in request["events"]:
        event_id = event["id"]
        if event_id in seen:
            duplicates += 1
            continue
        seen.add(event_id)
        customer = event["customer"].strip(ASCII_WHITESPACE)
        amount = event["amount_cents"]
        status = event["status"]
        if not customer or amount < 0 or status not in VALID_STATUSES:
            rejected += 1
            continue
        if status == "pending" or status == "void":
            ignored += 1
            continue
        row = customers.get(customer)
        if row is None:
            row = [0, 0, 0, 0]
            customers[customer] = row
        row[2] += 1
        if status == "paid":
            row[0] += amount
            if include_fees:
                row[3] += (amount * fee_bps + 5000) // 10000
        else:
            row[1] += amount
    # Aggregate totals once per customer instead of once per accepted event.
    accepted = gross = refunds = fees = 0
    rows = []
    for name in sorted(customers):
        paid, refunded, count, fee = customers[name]
        accepted += count
        gross += paid
        refunds += refunded
        fees += fee
        rows.append({"customer": name, "gross_cents": paid,
                     "refund_cents": refunded, "net_cents": paid - refunded - fee,
                     "count": count})
        if include_fees:
            rows[-1]["fee_cents"] = fee
    result = {
        "customers": rows,
        "accepted": accepted, "duplicates": duplicates, "ignored": ignored,
        "rejected": rejected, "gross_cents": gross, "refund_cents": refunds,
        "net_cents": gross - refunds - fees,
    }
    if include_fees:
        result["fee_cents"] = fees
    return result


def access_log(request):
    start, end = request["start_ms"], request["end_ms"]
    groups = {}
    for event in request["events"]:
        if not start <= event["ts_ms"] < end:
            continue
        route = event["route"].strip(ASCII_WHITESPACE)
        row = groups.get(route)
        if row is None:
            row = [0, 0, []]
            groups[route] = row
        error = event["status"] >= 500
        size = event["bytes"]
        row[0] += error
        row[1] += size
        row[2].append(event["duration_us"])
    routes = []
    total_count = total_errors = total_bytes = 0
    for route in sorted(groups):
        errors, size, durations = groups[route]
        durations.sort()
        n = len(durations)
        total_count += n
        total_errors += errors
        total_bytes += size
        routes.append({
            "route": route, "count": n, "errors": errors,
            "total_bytes": size, "max_us": durations[-1],
            "p95_us": durations[(95 * n - 1) // 100],
        })
    return {"routes": routes, "total_count": total_count,
            "total_errors": total_errors, "total_bytes": total_bytes}


def telemetry(request):
    samples = request["samples"]
    window = request["window"]
    if window <= 0 or window > len(samples):
        return {"error": "invalid_window"}
    threshold = request["threshold"]
    values = np.asarray(samples, dtype=np.int64)
    if window == 1:
        averages = values
    else:
        sums = np.empty(len(samples) - window + 1, dtype=np.int64)
        sums[0] = values[:window].sum(dtype=np.int64)
        # Accumulate window deltas so long prefixes cannot exceed int64.
        np.cumsum(values[window:] - values[:-window], out=sums[1:])
        sums[1:] += sums[0]
        averages = np.abs(sums) // window
        averages[sums < 0] *= -1
    count = len(averages)
    weights = np.arange(1, count + 1, dtype=np.int64)
    return {"count": count, "min": int(averages.min()),
            "max": int(averages.max()),
            "above": int(np.count_nonzero(averages > threshold)),
            "weighted_checksum": int(np.dot(weights, averages))}


OPERATIONS = {"invoice": invoice, "access_log": access_log, "telemetry": telemetry}


def invalid_constant(value):
    raise ValueError("Invalid JSON constant: " + value)


DECODER = json.JSONDecoder(parse_constant=invalid_constant)
ENCODER = json.JSONEncoder(ensure_ascii=True, separators=(",", ":"))


def process_line(line):
    try:
        request = DECODER.decode(line.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, RecursionError):
        return {"error": "invalid_json"}
    op = request.get("op") if isinstance(request, dict) else None
    operation = OPERATIONS.get(op) if isinstance(op, str) else None
    if operation is None:
        return {"error": "unknown_op"}
    return operation(request)


def main():
    if len(sys.argv) != 3:
        print("Usage: worker.sh INPUT_JSONL OUTPUT_JSONL", file=sys.stderr)
        return 2
    # Binary iteration preserves the protocol's LF framing; CRLF is JSON whitespace.
    with open(sys.argv[1], "rb") as source, open(sys.argv[2], "w", encoding="utf-8", newline="\n") as target:
        for line in source:
            if line.isspace():
                continue
            response = process_line(line)
            target.write(ENCODER.encode(response))
            target.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
