use serde::{Deserialize, Deserializer};
use serde::de::{DeserializeSeed, SeqAccess, Visitor};
use serde_json::{Value, json, value::RawValue};
use std::borrow::Cow;
use std::collections::{BTreeMap, HashSet};
use std::fmt;
use crate::{InvoiceTotal, RouteTotal, trim_ascii};

#[derive(Deserialize)]
struct Request<'a> {
    #[serde(borrow)]
    op: Cow<'a, str>,
    #[serde(borrow)]
    events: Option<&'a RawValue>,
    #[serde(borrow)]
    samples: Option<&'a RawValue>,
    start_ms: Option<i64>,
    end_ms: Option<i64>,
    window: Option<i64>,
    threshold: Option<i64>,
    #[serde(default, deserialize_with = "present_fee_bps")]
    fee_bps: Option<i64>,
}

fn present_fee_bps<'de, D: Deserializer<'de>>(d: D) -> Result<Option<i64>, D::Error> {
    i64::deserialize(d).map(Some)
}

#[derive(Deserialize)]
struct InvoiceEvent<'a> {
    #[serde(borrow)]
    id: Cow<'a, str>,
    #[serde(borrow)]
    customer: Cow<'a, str>,
    amount_cents: i64,
    #[serde(borrow)]
    status: Cow<'a, str>,
}

#[derive(Deserialize)]
struct AccessEvent<'a> {
    ts_ms: i64,
    #[serde(borrow)]
    route: Cow<'a, str>,
    status: i64,
    duration_us: i64,
    bytes: i64,
}

// Borrow ordinary identifiers directly from the input; escaped strings own only
// their decoded bytes. Trimming a decoded string keeps that same allocation.
fn normalized(s: Cow<'_, str>) -> Cow<'_, str> {
    match s {
        Cow::Borrowed(s) => Cow::Borrowed(trim_ascii(s)),
        Cow::Owned(mut s) => {
            let trimmed = trim_ascii(&s);
            let start = trimmed.as_ptr() as usize - s.as_ptr() as usize;
            let end = start + trimmed.len();
            s.truncate(end);
            if start != 0 { s.drain(..start); }
            Cow::Owned(s)
        }
    }
}

struct Invoice { fee_bps: Option<i64> }
impl<'de> DeserializeSeed<'de> for Invoice {
    type Value = Value;
    fn deserialize<D: Deserializer<'de>>(self, d: D) -> Result<Value, D::Error> {
        d.deserialize_seq(self)
    }
}
impl<'de> Visitor<'de> for Invoice {
    type Value = Value;
    fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result { f.write_str("invoice events") }
    fn visit_seq<S: SeqAccess<'de>>(self, mut seq: S) -> Result<Value, S::Error> {
        let mut seen = HashSet::new();
        let mut customers: BTreeMap<Cow<'de, str>, InvoiceTotal> = BTreeMap::new();
        let (mut accepted, mut duplicates, mut ignored, mut rejected) = (0i64, 0i64, 0i64, 0i64);
        let (mut gross, mut refund, mut fee) = (0i64, 0i64, 0i64);
        while let Some(event) = seq.next_element::<InvoiceEvent<'de>>()? {
            if !seen.insert(event.id) { duplicates += 1; continue; }
            let customer = normalized(event.customer);
            let amount = event.amount_cents;
            let status = event.status.as_ref();
            if customer.is_empty() || amount < 0 || !matches!(status, "paid" | "refund" | "pending" | "void") {
                rejected += 1; continue;
            }
            if matches!(status, "pending" | "void") { ignored += 1; continue; }
            accepted += 1;
            let row = customers.entry(customer).or_default();
            row.count += 1;
            if status == "paid" {
                row.gross += amount;
                gross += amount;
                if let Some(bps) = self.fee_bps {
                    let event_fee = (amount * bps + 5000) / 10000;
                    row.fee += event_fee;
                    fee += event_fee;
                }
            } else { row.refund += amount; refund += amount; }
        }
        let customers: Vec<Value> = customers.into_iter().map(|(customer, row)| {
            let mut value = json!({
                "customer":customer,"gross_cents":row.gross,"refund_cents":row.refund,
                "net_cents":row.gross-row.refund-row.fee,"count":row.count
            });
            if self.fee_bps.is_some() { value["fee_cents"] = json!(row.fee); }
            value
        }).collect();
        let mut result = json!({"customers":customers,"accepted":accepted,"duplicates":duplicates,
            "ignored":ignored,"rejected":rejected,"gross_cents":gross,
            "refund_cents":refund,"net_cents":gross-refund-fee});
        if self.fee_bps.is_some() { result["fee_cents"] = json!(fee); }
        Ok(result)
    }
}

struct Access { start: i64, end: i64 }
impl<'de> DeserializeSeed<'de> for Access {
    type Value = Value;
    fn deserialize<D: Deserializer<'de>>(self, d: D) -> Result<Value, D::Error> {
        d.deserialize_seq(self)
    }
}
impl<'de> Visitor<'de> for Access {
    type Value = Value;
    fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result { f.write_str("access events") }
    fn visit_seq<S: SeqAccess<'de>>(self, mut seq: S) -> Result<Value, S::Error> {
        let mut routes: BTreeMap<Cow<'de, str>, RouteTotal> = BTreeMap::new();
        let (mut total_count, mut total_errors, mut total_bytes) = (0i64, 0i64, 0i64);
        while let Some(event) = seq.next_element::<AccessEvent<'de>>()? {
            if event.ts_ms < self.start || event.ts_ms >= self.end { continue; }
            let errors = i64::from(event.status >= 500);
            let row = routes.entry(normalized(event.route)).or_default();
            row.errors += errors;
            row.bytes += event.bytes;
            row.durations.push(event.duration_us);
            total_count += 1;
            total_errors += errors;
            total_bytes += event.bytes;
        }
        let routes: Vec<Value> = routes.into_iter().map(|(route, mut row)| {
            let n = row.durations.len();
            let max_us = *row.durations.iter().max().unwrap();
            let (_, p95, _) = row.durations.select_nth_unstable(n - 1 - n / 20);
            json!({"route":route,"count":n,"errors":row.errors,"total_bytes":row.bytes,
                "max_us":max_us,"p95_us":*p95})
        }).collect();
        Ok(json!({"routes":routes,"total_count":total_count,"total_errors":total_errors,"total_bytes":total_bytes}))
    }
}

struct Telemetry { window: usize, threshold: i64 }
impl<'de> DeserializeSeed<'de> for Telemetry {
    type Value = Value;
    fn deserialize<D: Deserializer<'de>>(self, d: D) -> Result<Value, D::Error> {
        d.deserialize_seq(self)
    }
}
impl<'de> Visitor<'de> for Telemetry {
    type Value = Value;
    fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result { f.write_str("telemetry samples") }
    fn visit_seq<S: SeqAccess<'de>>(self, mut seq: S) -> Result<Value, S::Error> {
        let mut ring = Vec::new();
        let (mut cursor, mut count) = (0usize, 0i64);
        let (mut sum, mut min, mut max, mut above, mut checksum) =
            (0i64, i64::MAX, i64::MIN, 0i64, 0i64);
        while let Some(sample) = seq.next_element::<i64>()? {
            if ring.len() < self.window {
                ring.push(sample);
                sum += sample;
                if ring.len() < self.window { continue; }
            } else {
                sum -= ring[cursor];
                ring[cursor] = sample;
                sum += sample;
                cursor += 1;
                if cursor == self.window { cursor = 0; }
            }
            let average = sum / self.window as i64;
            count += 1;
            min = min.min(average);
            max = max.max(average);
            above += i64::from(average > self.threshold);
            checksum += count * average;
        }
        if count == 0 { return Ok(json!({"error":"invalid_window"})); }
        Ok(json!({"count":count,"min":min,"max":max,"above":above,"weighted_checksum":checksum}))
    }
}

pub fn process(line: &[u8]) -> Option<Value> {
    let request: Request<'_> = serde_json::from_slice(line).ok()?;
    match request.op.as_ref() {
        "invoice" => {
            let mut d = serde_json::Deserializer::from_str(request.events?.get());
            if request.fee_bps.is_some_and(|bps| !(0..=1000).contains(&bps)) { return None; }
            Invoice { fee_bps: request.fee_bps }.deserialize(&mut d).ok()
        }
        "access_log" => {
            let mut d = serde_json::Deserializer::from_str(request.events?.get());
            Access { start: request.start_ms?, end: request.end_ms? }.deserialize(&mut d).ok()
        }
        "telemetry" => {
            let window = request.window?;
            if window <= 0 {
                return Some(json!({"error":"invalid_window"}));
            }
            let mut d = serde_json::Deserializer::from_str(request.samples?.get());
            Telemetry { window: window as usize, threshold: request.threshold? }.deserialize(&mut d).ok()
        }
        _ => Some(json!({"error":"unknown_op"})),
    }
}
