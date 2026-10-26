"""Persistent, standard-library-only JSONL application worker."""
import json
import sys

ASCII_WHITESPACE = " \t\n\r\v\f"
VALID_STATUSES = frozenset(("paid", "refund", "pending", "void"))


def invoice(request):
    seen = set()
    customers = {}
    accepted = duplicates = ignored = rejected = gross = refunds = 0
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
        accepted += 1
        row = customers.get(customer)
        if row is None:
            row = [0, 0, 0]
            customers[customer] = row
        row[2] += 1
        if status == "paid":
            row[0] += amount
            gross += amount
        else:
            row[1] += amount
            refunds += amount
    return {
        "customers": [
            {"customer": name, "gross_cents": row[0],
             "refund_cents": row[1], "net_cents": row[0] - row[1],
             "count": row[2]}
            for name, row in sorted(customers.items())
        ],
        "accepted": accepted, "duplicates": duplicates, "ignored": ignored,
        "rejected": rejected, "gross_cents": gross, "refund_cents": refunds,
        "net_cents": gross - refunds,
    }


def access_log(request):
    start, end = request["start_ms"], request["end_ms"]
    groups = {}
    total_count = total_errors = total_bytes = 0
    for event in request["events"]:
        if not start <= event["ts_ms"] < end:
            continue
        route = event["route"].strip(ASCII_WHITESPACE)
        row = groups.get(route)
        if row is None:
            row = [0, 0, []]
            groups[route] = row
        error = int(event["status"] >= 500)
        size = event["bytes"]
        row[0] += error
        row[1] += size
        row[2].append(event["duration_us"])
        total_count += 1
        total_errors += error
        total_bytes += size
    routes = []
    for route, (errors, size, durations) in sorted(groups.items()):
        durations.sort()
        n = len(durations)
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
    rolling_sum = sum(samples[:window])
    average = (rolling_sum // window if rolling_sum >= 0
               else -((-rolling_sum) // window))
    minimum = maximum = checksum = average
    above = int(average > threshold)
    for end in range(window, len(samples)):
        rolling_sum += samples[end] - samples[end - window]
        average = (rolling_sum // window if rolling_sum >= 0
                   else -((-rolling_sum) // window))
        if average < minimum:
            minimum = average
        if average > maximum:
            maximum = average
        above += average > threshold
        checksum += (end - window + 2) * average
    return {"count": len(samples) - window + 1, "min": minimum,
            "max": maximum, "above": above, "weighted_checksum": checksum}


OPERATIONS = {"invoice": invoice, "access_log": access_log, "telemetry": telemetry}


def invalid_constant(value):
    raise ValueError("Invalid JSON constant: " + value)


def process_line(line):
    try:
        request = json.loads(line.decode("utf-8"), parse_constant=invalid_constant)
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
            if not line.strip():
                continue
            response = process_line(line)
            target.write(json.dumps(response, ensure_ascii=True, separators=(",", ":")))
            target.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
