// Deterministic correctness and persistent transport tests, entirely in BAML.
function decoded(text: string) -> baml.json.json {
    baml.json.parse(process(text))
}

test "published examples" {
    assert.equal(
        decoded(
            `{"op":"invoice","events":[{"id":"e1","customer":" A ","amount_cents":150,"status":"paid"}]}`,
        ),
        baml.json.parse(
            `{"customers":[{"customer":"A","gross_cents":150,"refund_cents":0,"net_cents":150,"count":1}],"accepted":1,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":150,"refund_cents":0,"net_cents":150}`,
        ),
    );
    assert.equal(
        decoded(
            `{"op":"access_log","start_ms":100,"end_ms":200,"events":[{"ts_ms":120,"route":" /api/orders ","status":503,"duration_us":1234,"bytes":20}]}`,
        ),
        baml.json.parse(
            `{"routes":[{"route":"/api/orders","count":1,"errors":1,"total_bytes":20,"max_us":1234,"p95_us":1234}],"total_count":1,"total_errors":1,"total_bytes":20}`,
        ),
    );
    assert.equal(
        decoded(`{"op":"telemetry","samples":[-2,5,8,1],"window":2,"threshold":3}`),
        baml.json.parse(`{"count":3,"min":1,"max":6,"above":2,"weighted_checksum":25}`),
    )
}

test "invoice dedup validation trim order and zero retention" {
    let events = [
        InvoiceEvent { id: "bad", customer: " \t\r\n\u000b\u000c", amount_cents: 2, status: "paid" },
        InvoiceEvent { id: "bad", customer: "later", amount_cents: 100, status: "paid" },
        InvoiceEvent { id: "1", customer: " z ", amount_cents: 9007199254740000, status: "paid" },
        InvoiceEvent { id: "2", customer: "z", amount_cents: 9007199254740000, status: "refund" },
        InvoiceEvent { id: "3", customer: "aa", amount_cents: 1, status: "refund" },
        InvoiceEvent { id: "4", customer: "B", amount_cents: 0, status: "paid" },
        InvoiceEvent { id: "5", customer: "unused", amount_cents: 0, status: "pending" },
        InvoiceEvent { id: "6", customer: "unused", amount_cents: 0, status: "void" },
        InvoiceEvent { id: "7", customer: "unused", amount_cents: -1, status: "pending" },
        InvoiceEvent { id: "8", customer: "unused", amount_cents: 0, status: "PAID" },
    ];
    let result = invoice(InvoiceRequest { events: events });
    assert.equal(result.accepted, 4);
    assert.equal(result.duplicates, 1);
    assert.equal(result.ignored, 2);
    assert.equal(result.rejected, 3);
    assert.equal(result.net_cents, -1);
    assert.equal(
        result.customers.map((c) -> {
            c.customer
        }),
        ["B", "aa", "z"],
    );
    assert.equal(result.customers[2].net_cents, 0);
    assert.equal(result.customers[2].count, 2);
    assert.equal(
        decoded(`{"op":"invoice","events":[]}`),
        baml.json.parse(
            `{"customers":[],"accepted":0,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":0,"refund_cents":0,"net_cents":0}`,
        ),
    );
    assert.equal(
        baml.json.parse(
            process(
                `{"op":"invoice","events":[{"id":"x","customer":"A","amount_cents":9007199254740991,"status":"paid"}]}`,
            ),
        ),
        baml.json.from(
            invoice(
                InvoiceRequest {
                    events: [
                        InvoiceEvent {
                            id: "x",
                            customer: "A",
                            amount_cents: 9007199254740991,
                            status: "paid",
                        },
                    ],
                },
            ),
            omit_nulls = true,
        ),
    )
}

test "access boundaries p95 exact bytes and lexicographic order" {
    let events: AccessEvent[] = [];
    let i = 21;
    while (i > 0) {
        events.push(
            AccessEvent {
                ts_ms: 100,
                route: " aa\t",
                status: if (i == 1) {
                    500
                } else {
                    499
                },
                duration_us: i,
                bytes: 3000000000,
            },
        );
        i -= 1;
    }
    events.push(
        AccessEvent { ts_ms: 199, route: "B", status: 999, duration_us: 9007199254740991, bytes: 0 },
    );
    events.push(
        AccessEvent { ts_ms: 200, route: "exclude", status: 500, duration_us: 1000, bytes: 1000 },
    );
    events.push(
        AccessEvent { ts_ms: 99, route: "exclude", status: 500, duration_us: 1000, bytes: 1000 },
    );
    let result = access_log(AccessRequest { start_ms: 100, end_ms: 200, events: events });
    assert.equal(
        result.routes.map((r) -> {
            r.route
        }),
        ["B", "aa"],
    );
    assert.equal(result.routes[1].p95_us, 20);
    assert.equal(result.routes[1].max_us, 21);
    assert.equal(result.total_count, 22);
    assert.equal(result.total_errors, 2);
    assert.equal(result.total_bytes, 63000000000);
    assert.equal(
        access_log(AccessRequest { start_ms: 200, end_ms: 100, events: events }).routes,
        [],
    );
    assert.equal(
        decoded(`{"op":"access_log","start_ms":0,"end_ms":1,"events":[]}`),
        baml.json.parse(`{"routes":[],"total_count":0,"total_errors":0,"total_bytes":0}`),
    )
}

test "telemetry against direct window oracle" {
    let samples: int[] = [];
    let seed = 381;
    let n = 0;
    while (n < 150) {
        seed = seed * 48271 % 2147483647;
        samples.push(seed % 20001 - 10000);
        n += 1;
    }
    let w = 1;
    while (w <= samples.length()) {
        let averages: int[] = [];
        let i = w - 1;
        while (i < samples.length()) {
            let sum = 0;
            let j = i - w + 1;
            while (j <= i) {
                sum += samples[j];
                j += 1;
            }
            averages.push(sum / w);
            i += 1;
        }
        let expected = TelemetryResult {
            count: averages.length(),
            min: averages[0],
            max: averages[0],
            above: 0,
            weighted_checksum: 0,
        };
        i = 0;
        for (let avg in averages) {
            if (avg < expected.min) {
                expected.min = avg;
            }
            if (avg > expected.max) {
                expected.max = avg;
            }
            if (avg > -57) {
                expected.above += 1;
            }
            expected.weighted_checksum += (i + 1) * avg;
            i += 1;
        }
        assert.equal(
            telemetry(TelemetryRequest { samples: samples, window: w, threshold: -57 }),
            expected,
        );
        w += 1;
    }
    assert.equal(
        telemetry(TelemetryRequest { samples: [], window: 1, threshold: 0 }),
        ErrorResult { error: "invalid_window" },
    );
    assert.equal(
        telemetry(TelemetryRequest { samples: [1], window: 0, threshold: 0 }),
        ErrorResult { error: "invalid_window" },
    );
    assert.equal(
        telemetry(TelemetryRequest { samples: [1], window: -1, threshold: 0 }),
        ErrorResult { error: "invalid_window" },
    );
    assert.equal(
        decoded(`{"op":"telemetry","samples":[-9007199254740991],"window":1,"threshold":0}`),
        baml.json.parse(
            `{"count":1,"min":-9007199254740991,"max":-9007199254740991,"above":0,"weighted_checksum":-9007199254740991}`,
        ),
    )
}

function prepare_files(input: string) -> void {
    let f = baml.fs.open(input, "w");
    defer { f.close(); }
    let a = `{"op":"invoice","events":[{"id":"x","customer":"A","amount_cents":4294967297,"status":"paid"}]}`;
    f.write("\r\n \t\r\n" + a + "\r\n");
    f.write(`{"op":"telemetry","samples":[-2,5,8,1],"window":2,"threshold":3}` + "\n");
    f.write(a + "\n{bad\n{\"op\":\"unknown\"}\n");
    f.write(
        `{"op":"telemetry","samples":[-5,-2],"window":2,"threshold":-4,"padding":"`
            + "x".repeat(102400)
            + `"}`
            + "\r\n",
    );
    let i = 0;
    while (i < 300) {
        f.write(`{"op":"invoice","events":[]}` + "\n");
        i += 1;
    }
    f.write("{\"op\":\"telemetry\",\"samples\":[1],\"window\":1,\"threshold\":0}");
}

function verify_files(output: string) -> void {
    let lines = baml.fs.read(output).trim_end().split("\n");
    assert.equal(lines.length(), 307);
    assert.equal(lines[0], lines[2]);
    assert.equal(
        baml.json.parse(lines[1]),
        baml.json.parse(`{"count":3,"min":1,"max":6,"above":2,"weighted_checksum":25}`),
    );
    assert.equal(baml.json.parse(lines[3]), baml.json.parse(`{"error":"invalid_json"}`));
    assert.equal(baml.json.parse(lines[4]), baml.json.parse(`{"error":"unknown_op"}`));
    assert.equal(
        baml.json.parse(lines[5]),
        baml.json.parse(`{"count":1,"min":-3,"max":-3,"above":1,"weighted_checksum":-3}`),
    );
    assert.equal(
        baml.json.parse(lines[306]),
        baml.json.parse(`{"count":1,"min":1,"max":1,"above":1,"weighted_checksum":1}`),
    );
}

test "persistent incremental transport" {
    prepare_files("test_input.jsonl");
    main("test_input.jsonl", "test_output.jsonl");
    verify_files("test_output.jsonl");
}

test "malformed JSON and UTF8 recovery" {
    let invalid = ["{", "[1,]", "{\"x\":}", "true false", "{\"x\":01}", "{\"x\":\"\\q\"}", "\"unfinished"];
    {
        let f = baml.fs.open("test_invalid_input.jsonl", "w");
        defer { f.close(); }
        for (let text in invalid) {
            f.write(text + "\n");
        }
        f.write(uint8array.from_array([255, 10]));
        f.write("null\n[]\n123\n\"unknown\"\n{\"op\":\"missing\"}\n");
        f.write(`{"op":"telemetry","samples":[5],"window":1,"threshold":3}`);
    };
    main("test_invalid_input.jsonl", "test_invalid_output.jsonl");
    let lines = baml.fs.read("test_invalid_output.jsonl").trim_end().split("\n");
    assert.equal(lines.length(), invalid.length() + 7);
    let i = 0;
    while (i < invalid.length() + 1) {
        assert.equal(baml.json.parse(lines[i]), baml.json.parse(`{"error":"invalid_json"}`));
        i += 1;
    }
    while (i < invalid.length() + 6) {
        assert.equal(baml.json.parse(lines[i]), baml.json.parse(`{"error":"unknown_op"}`));
        i += 1;
    }
    assert.equal(
        baml.json.parse(lines[i]),
        baml.json.parse(`{"count":1,"min":5,"max":5,"above":1,"weighted_checksum":5}`),
    )
}
