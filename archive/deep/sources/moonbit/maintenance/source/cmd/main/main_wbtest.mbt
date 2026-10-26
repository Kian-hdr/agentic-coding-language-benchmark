///|
fn check(request : String, expected : String) -> Unit raise {
  assert_eq(process(request), @json.parse(expected))
}

///|
test "spec examples" {
  check(
    (
      #|{"op":"invoice","events":[{"id":"e1","customer":" A ","amount_cents":150,"status":"paid"}]}
    ),
    (
      #|{"customers":[{"customer":"A","gross_cents":150,"refund_cents":0,"net_cents":150,"count":1}],"accepted":1,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":150,"refund_cents":0,"net_cents":150}
    ),
  )
  check(
    (
      #|{"op":"access_log","start_ms":100,"end_ms":200,"events":[{"ts_ms":120,"route":" /api/orders ","status":503,"duration_us":1234,"bytes":20}]}
    ),
    (
      #|{"routes":[{"route":"/api/orders","count":1,"errors":1,"total_bytes":20,"max_us":1234,"p95_us":1234}],"total_count":1,"total_errors":1,"total_bytes":20}
    ),
  )
  check(
    (
      #|{"op":"telemetry","samples":[-2,5,8,1],"window":2,"threshold":3}
    ),
    (
      #|{"count":3,"min":1,"max":6,"above":2,"weighted_checksum":25}
    ),
  )
}

///|
test "invoice dedup before validation, all whitespace and zero-net retention" {
  check(
    (
      #|{"op":"invoice","events":[{"id":"bad","customer":"","amount_cents":1,"status":"paid"},{"id":"bad","customer":"X","amount_cents":7,"status":"paid"},{"id":"p","customer":"P","amount_cents":4,"status":"pending"},{"id":"v","customer":"V","amount_cents":4,"status":"void"},{"id":"neg","customer":"N","amount_cents":-1,"status":"pending"},{"id":"status","customer":"N","amount_cents":0,"status":"other"},{"id":"1","customer":" \t\n\r\u000b\u000caa\u000b ","amount_cents":5000000000,"status":"paid"},{"id":"2","customer":"aa","amount_cents":5000000000,"status":"refund"},{"id":"3","customer":"z","amount_cents":0,"status":"paid"}]}
    ),
    (
      #|{"customers":[{"customer":"aa","gross_cents":5000000000,"refund_cents":5000000000,"net_cents":0,"count":2},{"customer":"z","gross_cents":0,"refund_cents":0,"net_cents":0,"count":1}],"accepted":3,"duplicates":1,"ignored":2,"rejected":3,"gross_cents":5000000000,"refund_cents":5000000000,"net_cents":0}
    ),
  )
}

///|
test "large exact numbers and exponent notation" {
  check(
    (
      #|{"op":"telemetry","samples":[9007199254740991],"window":1,"threshold":9007199254740990}
    ),
    (
      #|{"count":1,"min":9007199254740991,"max":9007199254740991,"above":1,"weighted_checksum":9007199254740991}
    ),
  )
  check(
    (
      #|{"op":"telemetry","samples":[-9007199254740991],"window":1e0,"threshold":0}
    ),
    (
      #|{"count":1,"min":-9007199254740991,"max":-9007199254740991,"above":0,"weighted_checksum":-9007199254740991}
    ),
  )
  check(
    (
      #|{"op":"telemetry","samples":[-7,-2,0],"window":2,"threshold":-2}
    ),
    (
      #|{"count":2,"min":-4,"max":-1,"above":1,"weighted_checksum":-6}
    ),
  )
}

///|
test "invalid windows, unknown operations, invalid JSON recovery" {
  for w in ["0", "-1", "3", "9007199254740991"] {
    check(
      "{\"op\":\"telemetry\",\"samples\":[1,2],\"window\":" +
      w +
      ",\"threshold\":0}",
      "{\"error\":\"invalid_window\"}",
    )
  }
  check(
    "{\"op\":\"telemetry\",\"samples\":[],\"window\":1,\"threshold\":0}", "{\"error\":\"invalid_window\"}",
  )
  for s in ["null", "{}", "{\"op\":\"other\"}"] {
    check(s, "{\"error\":\"unknown_op\"}")
  }
  for
    s in [
      "{", "[1,]", "{\"a\":NaN}", "{}garbage", "\"unterminated", "{\"a\":01}",
    ] {
    check(s, "{\"error\":\"invalid_json\"}")
  }
}

///|
test "empty aggregations" {
  check(
    "{\"op\":\"invoice\",\"events\":[]}", "{\"customers\":[],\"accepted\":0,\"duplicates\":0,\"ignored\":0,\"rejected\":0,\"gross_cents\":0,\"refund_cents\":0,\"net_cents\":0}",
  )
  check(
    "{\"op\":\"access_log\",\"start_ms\":2,\"end_ms\":1,\"events\":[]}", "{\"routes\":[],\"total_count\":0,\"total_errors\":0,\"total_bytes\":0}",
  )
}

///|
test "access bounds, ASCII order and nearest-rank p95" {
  let events : Array[Json] = []
  for i = 1; i <= 20; i = i + 1 {
    events.push(
      Json::object({
        "ts_ms": num(100L),
        "route": Json::string(" aa "),
        "status": num(if i == 20 { 500L } else { 499L }),
        "duration_us": num(i.to_int64()),
        "bytes": num(5000000000L),
      }),
    )
  }
  for ts in [99L, 199L, 200L] {
    events.push(
      Json::object({
        "ts_ms": num(ts),
        "route": Json::string("z"),
        "status": num(503L),
        "duration_us": num(6000000000L),
        "bytes": num(1L),
      }),
    )
  }
  let result = access_log(
    Json::object({
      "events": Json::array(events),
      "start_ms": num(100L),
      "end_ms": num(200L),
    }),
  )
  assert_eq(
    result,
    @json.parse(
      (
        #|{"routes":[{"route":"aa","count":20,"errors":1,"total_bytes":100000000000,"max_us":20,"p95_us":19},{"route":"z","count":1,"errors":1,"total_bytes":1,"max_us":6000000000,"p95_us":6000000000}],"total_count":21,"total_errors":2,"total_bytes":100000000001}
      ),
    ),
  )
}

///|
test "rolling algorithm compared with independent quadratic reference" {
  for n = 1; n <= 60; n = n + 1 {
    let samples = Array::makei(n, fn(i) {
      num(((i * 7919 + n * 31) % 10003 - 5001).to_int64())
    })
    for w = 1; w <= n; w = w + 1 {
      let averages : Array[Int64] = []
      for i = 0; i <= n - w; i = i + 1 {
        let mut total = 0L
        for k = i; k < i + w; k = k + 1 {
          total += integer(samples[k])
        }
        averages.push(total / w.to_int64())
      }
      let mut low = averages[0]
      let mut high = averages[0]
      let mut above = 0L
      let mut checksum = 0L
      for i, a in averages {
        if a < low {
          low = a
        }
        if a > high {
          high = a
        }
        if a > 10L {
          above += 1L
        }
        checksum += (i + 1).to_int64() * a
      }
      assert_eq(
        telemetry(
          Json::object({
            "samples": Json::array(samples),
            "window": num(w.to_int64()),
            "threshold": num(10L),
          }),
        ),
        Json::object({
          "count": num(averages.length().to_int64()),
          "min": num(low),
          "max": num(high),
          "above": num(above),
          "weighted_checksum": num(checksum),
        }),
      )
    }
  }
}

///|
async test "persistent bulk file, long lines, CRLF, blank lines, EOF and A B A isolation" {
  let root = "{ORIGINAL_BENCHMARK_ROOT}/deep_phase/runs/moonbit"
  let a = "{\"op\":\"telemetry\",\"samples\":[-2,5,8,1],\"window\":2,\"threshold\":3}"
  let b = "{\"op\":\"invoice\",\"events\":[]}"
  let long_samples = Array::make(60000, num(1L))
  let long = Json::object({
    "op": Json::string("telemetry"),
    "samples": Json::array(long_samples),
    "window": num(20000L),
    "threshold": num(0L),
    "padding": Json::string("UTF-8: 日本語 😀"),
  }).stringify()
  let lines = [a, b, "{broken", a, long]
  let input = @fs.open(
    root + "/Test_Input.jsonl",
    mode=WriteOnly,
    create_mode=CreateOrTruncate,
  )
  for i = 0; i < 305; i = i + 1 {
    input.write(" \t\r\n")
    input.write(lines[i % 5])
    if i < 304 {
      input.write(if i % 2 == 0 { "\r\n" } else { "\n" })
    }
  }
  input.close()
  let exit_code = @process.run(
    root + "/worker.sh",
    [root + "/Test_Input.jsonl", root + "/Test_Output.jsonl"],
    cwd="/private/tmp",
  )
  assert_eq(exit_code, 0)
  let output = @fs.open(root + "/Test_Output.jsonl", mode=ReadOnly)
  defer output.close()
  let mut n = 0
  while output.read_until("\n") is Some(line) {
    let value = @json.parse(line)
    if n % 5 == 4 {
      assert_eq(
        value,
        @json.parse(
          "{\"count\":40001,\"min\":1,\"max\":1,\"above\":40001,\"weighted_checksum\":800060001}",
        ),
      )
    } else {
      assert_eq(value, process(lines[n % 5]))
    }
    n += 1
  }
  assert_eq(n, 305)
}

///|
test "numeric JSON tokens retain exact decimal output" {
  for
    value in [
      9007199254740991L, 9007199254740990L, -9007199254740991L, 4294967297L, -4294967297L,
    ] {
    let text = value.to_string()
    let request = "{\"op\":\"telemetry\",\"samples\":[" +
      text +
      "],\"window\":1,\"threshold\":0}"
    let result = process(request)
    assert_eq(field(result, "min").stringify(), text)
    assert_eq(field(result, "weighted_checksum").stringify(), text)
  }
}

///|
test "invoice fees round per paid event after dedup and validation" {
  check(
    (
      #|{"op":"invoice","fee_bps":1000,"events":[{"id":"1","customer":" A ","amount_cents":4,"status":"paid"},{"id":"2","customer":"A","amount_cents":5,"status":"paid"},{"id":"3","customer":"A","amount_cents":5,"status":"paid"},{"id":"3","customer":"A","amount_cents":100,"status":"paid"},{"id":"4","customer":"A","amount_cents":20,"status":"refund"},{"id":"5","customer":"B","amount_cents":10,"status":"refund"},{"id":"6","customer":"Z","amount_cents":0,"status":"paid"},{"id":"bad","customer":"","amount_cents":100,"status":"paid"},{"id":"bad","customer":"B","amount_cents":100,"status":"paid"},{"id":"neg","customer":"B","amount_cents":-1,"status":"paid"},{"id":"s","customer":"B","amount_cents":100,"status":"other"},{"id":"p","customer":"B","amount_cents":100,"status":"pending"},{"id":"v","customer":"B","amount_cents":100,"status":"void"}]}
    ),
    (
      #|{"customers":[{"customer":"A","gross_cents":14,"refund_cents":20,"fee_cents":2,"net_cents":-8,"count":4},{"customer":"B","gross_cents":0,"refund_cents":10,"fee_cents":0,"net_cents":-10,"count":1},{"customer":"Z","gross_cents":0,"refund_cents":0,"fee_cents":0,"net_cents":0,"count":1}],"accepted":6,"duplicates":2,"ignored":2,"rejected":3,"gross_cents":14,"refund_cents":30,"fee_cents":2,"net_cents":-18}
    ),
  )
}

///|
test "invoice optional zero fee preserves legacy amounts and schema when absent" {
  let events = "\"events\":[{\"id\":\"1\",\"customer\":\"A\",\"amount_cents\":9007199254740991,\"status\":\"paid\"}]"
  let legacy = "{\"op\":\"invoice\"," + events + "}"
  let expected = "{\"customers\":[{\"customer\":\"A\",\"gross_cents\":9007199254740991,\"refund_cents\":0,\"net_cents\":9007199254740991,\"count\":1}],\"accepted\":1,\"duplicates\":0,\"ignored\":0,\"rejected\":0,\"gross_cents\":9007199254740991,\"refund_cents\":0,\"net_cents\":9007199254740991}"
  check(legacy, expected)
  check(
    "{\"op\":\"invoice\",\"fee_bps\":0," + events + "}",
    (
      #|{"customers":[{"customer":"A","gross_cents":9007199254740991,"refund_cents":0,"fee_cents":0,"net_cents":9007199254740991,"count":1}],"accepted":1,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":9007199254740991,"refund_cents":0,"fee_cents":0,"net_cents":9007199254740991}
    ),
  )
  check(legacy, expected)
  for bps in ["0", "1000"] {
    check(
      "{\"op\":\"invoice\",\"fee_bps\":" + bps + ",\"events\":[]}",
      "{\"customers\":[],\"accepted\":0,\"duplicates\":0,\"ignored\":0,\"rejected\":0,\"gross_cents\":0,\"refund_cents\":0,\"fee_cents\":0,\"net_cents\":0}",
    )
  }
}

///|
test "invoice fee exact near safe intermediate limit" {
  check(
    (
      #|{"op":"invoice","fee_bps":1,"events":[{"id":"1","customer":"A","amount_cents":9007199254735991,"status":"paid"}]}
    ),
    (
      #|{"customers":[{"customer":"A","gross_cents":9007199254735991,"refund_cents":0,"fee_cents":900719925474,"net_cents":9006298534810517,"count":1}],"accepted":1,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":9007199254735991,"refund_cents":0,"fee_cents":900719925474,"net_cents":9006298534810517}
    ),
  )
}
