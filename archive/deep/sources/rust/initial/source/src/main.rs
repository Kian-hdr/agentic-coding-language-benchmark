use serde_json::{Value, json};
use std::collections::{BTreeMap, HashSet};
use std::fs::File;
use std::io::{self, BufRead, BufReader, BufWriter, Write};

fn trim_ascii(s: &str) -> &str {
    s.trim_matches(|c| matches!(c, ' ' | '\t' | '\n' | '\r' | '\u{b}' | '\u{c}'))
}

#[derive(Default)]
struct InvoiceTotal {
    gross: i64,
    refund: i64,
    count: i64,
}

fn invoice(request: &Value) -> Option<Value> {
    let events = request.get("events")?.as_array()?;
    let mut seen = HashSet::with_capacity(events.len());
    let mut customers: BTreeMap<&str, InvoiceTotal> = BTreeMap::new();
    let (mut accepted, mut duplicates, mut ignored, mut rejected) = (0i64, 0i64, 0i64, 0i64);
    let (mut gross, mut refund) = (0i64, 0i64);
    for event in events {
        let id = event.get("id")?.as_str()?;
        if !seen.insert(id) {
            duplicates += 1;
            continue;
        }
        let customer = trim_ascii(event.get("customer")?.as_str()?);
        let amount = event.get("amount_cents")?.as_i64()?;
        let status = event.get("status")?.as_str()?;
        if customer.is_empty() || amount < 0 || !matches!(status, "paid" | "refund" | "pending" | "void") {
            rejected += 1;
            continue;
        }
        if matches!(status, "pending" | "void") {
            ignored += 1;
            continue;
        }
        accepted += 1;
        let row = customers.entry(customer).or_default();
        row.count += 1;
        if status == "paid" {
            row.gross += amount;
            gross += amount;
        } else {
            row.refund += amount;
            refund += amount;
        }
    }
    let customers: Vec<Value> = customers.into_iter().map(|(customer, row)| json!({
        "customer": customer, "gross_cents": row.gross, "refund_cents": row.refund,
        "net_cents": row.gross - row.refund, "count": row.count
    })).collect();
    Some(json!({"customers": customers, "accepted": accepted, "duplicates": duplicates,
        "ignored": ignored, "rejected": rejected, "gross_cents": gross,
        "refund_cents": refund, "net_cents": gross - refund}))
}

#[derive(Default)]
struct RouteTotal {
    errors: i64,
    bytes: i64,
    durations: Vec<i64>,
}

fn access_log(request: &Value) -> Option<Value> {
    let start = request.get("start_ms")?.as_i64()?;
    let end = request.get("end_ms")?.as_i64()?;
    let mut routes: BTreeMap<&str, RouteTotal> = BTreeMap::new();
    let (mut total_count, mut total_errors, mut total_bytes) = (0i64, 0i64, 0i64);
    for event in request.get("events")?.as_array()? {
        let ts = event.get("ts_ms")?.as_i64()?;
        if ts < start || ts >= end { continue; }
        let route = trim_ascii(event.get("route")?.as_str()?);
        let errors = i64::from(event.get("status")?.as_i64()? >= 500);
        let bytes = event.get("bytes")?.as_i64()?;
        let duration = event.get("duration_us")?.as_i64()?;
        let row = routes.entry(route).or_default();
        row.errors += errors;
        row.bytes += bytes;
        row.durations.push(duration);
        total_count += 1;
        total_errors += errors;
        total_bytes += bytes;
    }
    let routes: Vec<Value> = routes.into_iter().map(|(route, mut row)| {
        let n = row.durations.len();
        let max_us = *row.durations.iter().max().unwrap();
        // ceil(95*n/100)-1 equals n-1-floor(n/20), without multiplication overflow.
        let p95_index = n - 1 - n / 20;
        let (_, p95, _) = row.durations.select_nth_unstable(p95_index);
        json!({"route": route, "count": n, "errors": row.errors, "total_bytes": row.bytes,
            "max_us": max_us, "p95_us": *p95})
    }).collect();
    Some(json!({"routes": routes, "total_count": total_count,
        "total_errors": total_errors, "total_bytes": total_bytes}))
}

fn telemetry(request: &Value) -> Option<Value> {
    let samples = request.get("samples")?.as_array()?;
    let window = request.get("window")?.as_i64()?;
    if window <= 0 || window as u64 > samples.len() as u64 {
        return Some(json!({"error": "invalid_window"}));
    }
    let window = window as usize;
    let threshold = request.get("threshold")?.as_i64()?;
    let mut sum = 0i64;
    for sample in &samples[..window] { sum += sample.as_i64()?; }
    let count = samples.len() - window + 1;
    let (mut min, mut max, mut above, mut checksum) = (i64::MAX, i64::MIN, 0i64, 0i64);
    for i in 0..count {
        if i > 0 {
            sum -= samples[i - 1].as_i64()?;
            sum += samples[i + window - 1].as_i64()?;
        }
        let average = sum / window as i64;
        min = min.min(average);
        max = max.max(average);
        above += i64::from(average > threshold);
        checksum += (i as i64 + 1) * average;
    }
    Some(json!({"count": count, "min": min, "max": max,
        "above": above, "weighted_checksum": checksum}))
}

fn process(line: &[u8]) -> Value {
    let request: Value = match serde_json::from_slice(line) {
        Ok(request) => request,
        Err(_) => return json!({"error": "invalid_json"}),
    };
    let result = match request.get("op").and_then(Value::as_str) {
        Some("invoice") => invoice(&request),
        Some("access_log") => access_log(&request),
        Some("telemetry") => telemetry(&request),
        _ => return json!({"error": "unknown_op"}),
    };
    result.unwrap_or_else(|| json!({"error": "invalid_request"}))
}

fn bulk<R: BufRead, W: Write>(mut input: R, mut output: W) -> io::Result<()> {
    let mut line = Vec::new();
    loop {
        line.clear();
        if input.read_until(b'\n', &mut line)? == 0 { break; }
        if line.iter().all(|b| matches!(b, b' ' | b'\t' | b'\n' | b'\r' | 11 | 12)) { continue; }
        let response = process(&line);
        serde_json::to_writer(&mut output, &response)?;
        output.write_all(b"\n")?;
    }
    output.flush()
}

fn run() -> io::Result<()> {
    let args: Vec<_> = std::env::args_os().collect();
    if args.len() != 3 {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "usage: worker.sh INPUT_JSONL OUTPUT_JSONL"));
    }
    // Open before creating output so input-open errors cannot truncate output.
    let input = BufReader::new(File::open(&args[1])?);
    if std::fs::canonicalize(&args[1])? == std::fs::canonicalize(&args[2]).unwrap_or_default() {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "input and output must be different files"));
    }
    let output = BufWriter::new(File::create(&args[2])?);
    bulk(input, output)
}

fn main() {
    if let Err(error) = run() {
        eprintln!("worker: {error}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn evaluate(request: Value) -> Value {
        process(&serde_json::to_vec(&request).unwrap())
    }

    #[test]
    fn supplied_examples() {
        assert_eq!(evaluate(json!({"op":"invoice","events":[
            {"id":"e1","customer":" A ","amount_cents":150,"status":"paid"}]})),
            json!({"customers":[{"customer":"A","gross_cents":150,"refund_cents":0,
                "net_cents":150,"count":1}],"accepted":1,"duplicates":0,"ignored":0,
                "rejected":0,"gross_cents":150,"refund_cents":0,"net_cents":150}));
        assert_eq!(evaluate(json!({"op":"access_log","start_ms":100,"end_ms":200,
            "events":[{"ts_ms":120,"route":" /api/orders ","status":503,"duration_us":1234,"bytes":20}]})),
            json!({"routes":[{"route":"/api/orders","count":1,"errors":1,"total_bytes":20,
                "max_us":1234,"p95_us":1234}],"total_count":1,"total_errors":1,"total_bytes":20}));
        assert_eq!(evaluate(json!({"op":"telemetry","samples":[-2,5,8,1],"window":2,"threshold":3})),
            json!({"count":3,"min":1,"max":6,"above":2,"weighted_checksum":25}));
    }

    #[test]
    fn invoice_deduplication_validation_order_and_zero_net() {
        let result = evaluate(json!({"op":"invoice","events":[
            {"id":"bad","customer":" \t\r\n\u{b}\u{c}","amount_cents":10,"status":"paid"},
            {"id":"bad","customer":"A","amount_cents":100,"status":"paid"},
            {"id":"p","customer":" \tZ\u{b}","amount_cents":4_000_000_001i64,"status":"paid"},
            {"id":"r","customer":"Z","amount_cents":4_000_000_001i64,"status":"refund"},
            {"id":"a","customer":"AA","amount_cents":0,"status":"refund"},
            {"id":"b","customer":"B","amount_cents":2,"status":"paid"},
            {"id":"i","customer":"ignored","amount_cents":0,"status":"void"},
            {"id":"j","customer":"ignored","amount_cents":9,"status":"pending"},
            {"id":"n","customer":"X","amount_cents":-1,"status":"pending"},
            {"id":"s","customer":"X","amount_cents":1,"status":"invalid"},
            {"id":"s","customer":"X","amount_cents":1,"status":"paid"}
        ]}));
        assert_eq!(result, json!({"customers":[
            {"customer":"AA","gross_cents":0,"refund_cents":0,"net_cents":0,"count":1},
            {"customer":"B","gross_cents":2,"refund_cents":0,"net_cents":2,"count":1},
            {"customer":"Z","gross_cents":4_000_000_001i64,"refund_cents":4_000_000_001i64,"net_cents":0,"count":2}
        ],"accepted":4,"duplicates":2,"ignored":2,"rejected":3,
            "gross_cents":4_000_000_003i64,"refund_cents":4_000_000_001i64,"net_cents":2}));
        assert_eq!(trim_ascii("\u{a0}A\u{a0}"), "\u{a0}A\u{a0}");
    }

    #[test]
    fn empty_and_invalid_cases() {
        assert_eq!(evaluate(json!({"op":"invoice","events":[]})), json!({
            "customers":[],"accepted":0,"duplicates":0,"ignored":0,"rejected":0,
            "gross_cents":0,"refund_cents":0,"net_cents":0}));
        assert_eq!(evaluate(json!({"op":"access_log","events":[],"start_ms":2,"end_ms":1})),
            json!({"routes":[],"total_count":0,"total_errors":0,"total_bytes":0}));
        for window in [-1, 0, 4, 9_007_199_254_740_991i64] {
            assert_eq!(evaluate(json!({"op":"telemetry","samples":[1,2,3],"window":window,"threshold":0})),
                json!({"error":"invalid_window"}));
        }
        assert_eq!(evaluate(json!({"op":"telemetry","samples":[],"window":1,"threshold":0})),
            json!({"error":"invalid_window"}));
        for bytes in [b"{".as_slice(), b"{} garbage", b"\xff", b"{\"op\":NaN}", b"[1,]"] {
            assert_eq!(process(bytes), json!({"error":"invalid_json"}));
        }
        assert_eq!(evaluate(json!({"op":"other"})), json!({"error":"unknown_op"}));
    }

    #[test]
    fn telemetry_matches_naive_for_every_window() {
        let mut seed = 123456789u64;
        for n in 1..90 {
            let samples: Vec<i64> = (0..n).map(|_| {
                seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
                (seed >> 32) as i64 % 100_000 - 50_000
            }).collect();
            for window in 1..=n {
                let averages: Vec<i64> = samples.windows(window)
                    .map(|w| w.iter().sum::<i64>() / window as i64).collect();
                let expected = json!({"count": averages.len(), "min": averages.iter().min().unwrap(),
                    "max": averages.iter().max().unwrap(),
                    "above": averages.iter().filter(|&&a| a > -3).count(),
                    "weighted_checksum": averages.iter().enumerate().map(|(i,a)| (i as i64 + 1)*a).sum::<i64>()});
                assert_eq!(evaluate(json!({"op":"telemetry","samples":samples,"window":window,"threshold":-3})), expected);
            }
        }
    }

    #[test]
    fn exact_large_integers_and_negative_truncation() {
        let big = 9_007_199_254_740_991i64;
        assert_eq!(evaluate(json!({"op":"telemetry","samples":[big],"window":1,"threshold":big})),
            json!({"count":1,"min":big,"max":big,"above":0,"weighted_checksum":big}));
        assert_eq!(evaluate(json!({"op":"telemetry","samples":[-8,3,-4],"window":2,"threshold":-3})),
            json!({"count":2,"min":-2,"max":0,"above":2,"weighted_checksum":-2}));
    }

    #[test]
    fn access_boundaries_sorting_and_percentile_ranks() {
        for n in 1..=125usize {
            let mut events: Vec<Value> = (0..n).rev().map(|i| json!({"ts_ms":100,
                "route":" \tAA\r\n", "status":if i%2==0 {500} else {499},
                "duration_us":i as i64 + 5_000_000_000i64,"bytes":3_000_000_000i64})).collect();
            events.push(json!({"ts_ms":199,"route":"B","status":200,"duration_us":0,"bytes":0}));
            events.push(json!({"ts_ms":99,"route":"excluded","status":503,"duration_us":999,"bytes":1}));
            events.push(json!({"ts_ms":200,"route":"excluded","status":503,"duration_us":999,"bytes":1}));
            let actual = evaluate(json!({"op":"access_log","start_ms":100,"end_ms":200,"events":events}));
            let p95 = (95*n).div_ceil(100)-1;
            assert_eq!(actual, json!({"routes":[
                {"route":"AA","count":n,"errors":n.div_ceil(2),"total_bytes":n as i64*3_000_000_000i64,
                    "max_us":n as i64-1+5_000_000_000i64,"p95_us":p95 as i64+5_000_000_000i64},
                {"route":"B","count":1,"errors":0,"total_bytes":0,"max_us":0,"p95_us":0}
            ],"total_count":n+1,"total_errors":n.div_ceil(2),"total_bytes":n as i64*3_000_000_000i64}));
        }
    }

    #[test]
    fn bulk_framing_long_lines_and_independence() {
        let a = json!({"op":"invoice","events":[{"id":"e","customer":"A","amount_cents":1,"status":"paid"}]});
        let long = json!({"op":"unknown", "padding":"x".repeat(150_000)});
        let mut input = format!(" \t\r\n{a}\r\n{{bad\n{long}\n").into_bytes();
        input.extend_from_slice(b"\xff\n");
        input.extend_from_slice(a.to_string().as_bytes());
        let mut output = Vec::new();
        bulk(io::Cursor::new(input), &mut output).unwrap();
        let lines: Vec<Value> = output.split(|&b| b == b'\n').filter(|b| !b.is_empty())
            .map(|b| serde_json::from_slice(b).unwrap()).collect();
        assert_eq!(lines.len(), 5);
        assert_eq!(lines[0], lines[4]);
        assert_eq!(lines[1], json!({"error":"invalid_json"}));
        assert_eq!(lines[2], json!({"error":"unknown_op"}));
        assert_eq!(lines[3], json!({"error":"invalid_json"}));
    }
}
