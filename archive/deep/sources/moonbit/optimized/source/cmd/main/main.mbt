// All specified JSON integers are exactly representable at the JSON Double
// boundary. Convert immediately; every computation below uses Int64.

///|
fn integer(j : Json) -> Int64 {
  match j {
    Number(v, ..) => v.to_int64()
    _ => 0L
  }
}

///|
fn num(n : Int64) -> Json {
  Json::number(n.to_double(), repr=n.to_string())
}

///|
fn field(j : Json, key : String) -> Json {
  match j {
    Object(m) => m.get(key).unwrap_or(Json::null())
    _ => Json::null()
  }
}

///|
fn str(j : Json) -> String {
  match j {
    String(s) => s
    _ => ""
  }
}

///|
fn arr(j : Json) -> Array[Json] {
  match j {
    Array(a) => a
    _ => []
  }
}

///|
fn trim(s : String) -> String {
  s.trim(chars=" \t\n\r\u000b\u000c").to_owned()
}

///|
struct Customer {
  mut gross : Int64
  mut refund : Int64
  mut count : Int64
}

///|
fn invoice(j : Json) -> Json {
  let seen : Map[String, Bool] = Map([])
  let customers : Map[String, Customer] = Map([])
  let mut accepted = 0L
  let mut duplicates = 0L
  let mut ignored = 0L
  let mut rejected = 0L
  let mut gross = 0L
  let mut refund = 0L
  for e in arr(field(j, "events")) {
    let id = str(field(e, "id"))
    if seen.contains(id) {
      duplicates += 1L
      continue
    }
    seen[id] = true
    let name = trim(str(field(e, "customer")))
    let amount = integer(field(e, "amount_cents"))
    let status = str(field(e, "status"))
    if name == "" ||
      amount < 0L ||
      (
        status != "paid" &&
        status != "refund" &&
        status != "pending" &&
        status != "void"
      ) {
      rejected += 1L
      continue
    }
    if status == "pending" || status == "void" {
      ignored += 1L
      continue
    }
    accepted += 1L
    let c = customers.get_or_init(name, fn() {
      { gross: 0L, refund: 0L, count: 0L, }
    })
    c.count += 1L
    if status == "paid" {
      c.gross += amount
      gross += amount
    } else {
      c.refund += amount
      refund += amount
    }
  }
  let keys = customers.keys().to_array()
  keys.sort_by(fn(a, b) { a.lexical_compare(b) })
  let rows = keys.map(fn(name) {
    let c = customers.get(name).unwrap()
    Json::object({
      "customer": Json::string(name),
      "gross_cents": num(c.gross),
      "refund_cents": num(c.refund),
      "net_cents": num(c.gross - c.refund),
      "count": num(c.count),
    })
  })
  Json::object({
    "customers": Json::array(rows),
    "accepted": num(accepted),
    "duplicates": num(duplicates),
    "ignored": num(ignored),
    "rejected": num(rejected),
    "gross_cents": num(gross),
    "refund_cents": num(refund),
    "net_cents": num(gross - refund),
  })
}

///|
struct Route {
  mut errors : Int64
  mut bytes : Int64
  mut max_us : Int64
  durations : Array[Int64]
}

///|
// Three-way partition handles repeated durations in one pass. Bound total
// partition work, then fall back to sorting for adversarial pivot sequences.
fn select_duration(values : Array[Int64], k : Int) -> Int64 {
  let mut lo = 0
  let mut hi = values.length()
  let mut budget = 4L * hi.to_int64()
  while hi - lo > 1 {
    budget -= (hi - lo).to_int64()
    if budget < 0L {
      values.sort()
      return values[k]
    }
    let a = values[lo]
    let b = values[lo + (hi - lo) / 2]
    let c = values[hi - 1]
    let pivot = if a < b {
      if b < c { b } else if a < c { c } else { a }
    } else {
      if a < c { a } else if b < c { c } else { b }
    }
    let mut lt = lo
    let mut i = lo
    let mut gt = hi
    while i < gt {
      let v = values[i]
      if v < pivot {
        values[i] = values[lt]
        values[lt] = v
        lt += 1
        i += 1
      } else if v > pivot {
        gt -= 1
        values[i] = values[gt]
        values[gt] = v
      } else {
        i += 1
      }
    }
    if k < lt {
      hi = lt
    } else if k >= gt {
      lo = gt
    } else {
      return pivot
    }
  }
  values[k]
}

///|
fn access_log(j : Json) -> Json {
  let start = integer(field(j, "start_ms"))
  let end = integer(field(j, "end_ms"))
  let routes : Map[String, Route] = Map([])
  let mut count = 0L
  let mut errors = 0L
  let mut bytes = 0L
  for e in arr(field(j, "events")) {
    let ts = integer(field(e, "ts_ms"))
    if ts < start || ts >= end {
      continue
    }
    let name = trim(str(field(e, "route")))
    let r = routes.get_or_init(name, fn() {
      { errors: 0L, bytes: 0L, max_us: 0L, durations: [], }
    })
    let nbytes = integer(field(e, "bytes"))
    let duration = integer(field(e, "duration_us"))
    r.durations.push(duration)
    if duration > r.max_us {
      r.max_us = duration
    }
    r.bytes += nbytes
    bytes += nbytes
    count += 1L
    if integer(field(e, "status")) >= 500L {
      r.errors += 1L
      errors += 1L
    }
  }
  let keys = routes.keys().to_array()
  keys.sort_by(fn(a, b) { a.lexical_compare(b) })
  let rows = keys.map(fn(name) {
    let r = routes.get(name).unwrap()
    let n = r.durations.length()
    let p95 = ((95L * n.to_int64() + 99L) / 100L - 1L).to_int()
    Json::object({
      "route": Json::string(name),
      "count": num(n.to_int64()),
      "errors": num(r.errors),
      "total_bytes": num(r.bytes),
      "max_us": num(r.max_us),
      "p95_us": num(select_duration(r.durations, p95)),
    })
  })
  Json::object({
    "routes": Json::array(rows),
    "total_count": num(count),
    "total_errors": num(errors),
    "total_bytes": num(bytes),
  })
}

///|
fn telemetry(j : Json) -> Json {
  let samples = arr(field(j, "samples"))
  let window = integer(field(j, "window"))
  if window <= 0L || window > samples.length().to_int64() {
    return Json::object({ "error": Json::string("invalid_window") })
  }
  let w = window.to_int()
  let threshold = integer(field(j, "threshold"))
  let mut sum = 0L
  let mut count = 0L
  let mut low = 0L
  let mut high = 0L
  let mut above = 0L
  let mut checksum = 0L
  for i = 0; i < samples.length(); i = i + 1 {
    // Remove the outgoing sample first to avoid an unnecessary w+1 sum.
    if i >= w {
      sum -= integer(samples[i - w])
    }
    sum += integer(samples[i])
    if i >= w - 1 {
      let avg = sum / window
      count += 1L
      if count == 1L || avg < low {
        low = avg
      }
      if count == 1L || avg > high {
        high = avg
      }
      if avg > threshold {
        above += 1L
      }
      checksum += count * avg
    }
  }
  Json::object({
    "count": num(count),
    "min": num(low),
    "max": num(high),
    "above": num(above),
    "weighted_checksum": num(checksum),
  })
}

///|
fn process(line : String) -> Json {
  let j = @json.parse(line) catch {
    _ => return Json::object({ "error": Json::string("invalid_json") })
  }
  match str(field(j, "op")) {
    "invoice" => invoice(j)
    "access_log" => access_log(j)
    "telemetry" => telemetry(j)
    _ => Json::object({ "error": Json::string("unknown_op") })
  }
}

///|
async fn main {
  let args = @env.args()
  let input = @fs.open(args[1], mode=ReadOnly)
  defer input.close()
  let output = @fs.open(args[2], mode=WriteOnly, create_mode=CreateOrTruncate)
  defer output.close()
  let buffered = @io.BufferedWriter::new(output, size=65536)
  while input.read_until("\n") is Some(line) {
    if line.trim(chars=" \t\n\r\u000b\u000c").is_empty() {
      continue
    }
    buffered.write(process(line).stringify())
    buffered.write("\n")
  }
  buffered.flush()
}
