// Selection oracle and reproducible local performance fixture.
function prepare_benchmark(path: string) -> void {
    let output = baml.fs.open(path, "w");
    defer { output.close(); }
    let events: AccessEvent[] = [];
    let seed = 417;
    let i = 0;
    while (i < 1024) {
        seed = seed * 48271 % 2147483647;
        events.push(
            AccessEvent {
                ts_ms: i % 100,
                route: " /route/" + (i % 8).to_string() + " ",
                status: 200 + i % 401,
                duration_us: seed % 100000,
                bytes: i * 13,
            },
        );
        i += 1;
    }
    let line = `{"op":"access_log","start_ms":0,"end_ms":100,"events":` + baml.json.stringify(events) + "}\n";
    i = 0;
    while (i < 128) {
        output.write(line);
        i += 1;
    }
}

test "selection matches sorted oracle" {
    let seed = 781;
    let n = 1;
    while (n <= 220) {
        let random: int[] = [];
        let ascending: int[] = [];
        let descending: int[] = [];
        let repeated: int[] = [];
        let organ: int[] = [];
        let i = 0;
        while (i < n) {
            seed = seed * 48271 % 2147483647;
            random.push(seed % 9007199254740991);
            ascending.push(i * 3000000000);
            descending.push((n - i) * 3000000000);
            repeated.push(i % 3);
            organ.push(
                if (i < n / 2) {
                    i
                } else {
                    n - i
                },
            );
            i += 1;
        }
        for (let values in [random, ascending, descending, repeated, organ]) {
            let sorted = values.slice(0, n).sort_by((a, b) -> {
                a.cmp(b)
            });
            for (let k in [0, n / 2, (95 * n + 99) / 100 - 1, n - 1]) {
                assert.equal(select_duration(values.slice(0, n), k), sorted[k]);
            }
        }
        n += 1;
    }
    assert.equal(select_duration([9007199254740991, 0, 9007199254740990], 1), 9007199254740990)
}

function prepare_other_benchmarks() -> void {
    let events: InvoiceEvent[] = [];
    let samples: int[] = [];
    let i = 0;
    while (i < 1024) {
        events.push(
            InvoiceEvent {
                id: (i % 900).to_string(),
                customer: " customer/" + (i % 40).to_string() + " ",
                amount_cents: i * 12345,
                status: if (i % 7 == 0) {
                    "refund"
                } else {
                    "paid"
                },
            },
        );
        i += 1;
    }
    i = 0;
    let seed = 419;
    while (i < 8192) {
        seed = seed * 48271 % 2147483647;
        samples.push(seed % 2001 - 1000);
        i += 1;
    }
    let invoice_output = baml.fs.open("optimization_invoice_input.jsonl", "w");
    defer { invoice_output.close(); }
    let telemetry_output = baml.fs.open("optimization_telemetry_input.jsonl", "w");
    defer { telemetry_output.close(); }
    let invoice_line = `{"op":"invoice","events":` + baml.json.stringify(events) + "}\n";
    let telemetry_line = `{"op":"telemetry","window":47,"threshold":0,"samples":` + baml.json.stringify(samples) + "}\n";
    i = 0;
    while (i < 128) {
        invoice_output.write(invoice_line);
        telemetry_output.write(telemetry_line);
        i += 1;
    }
}

test "ASCII trimming preserves nonASCII whitespace" {
    assert.equal(trim_ascii(" \t\n\r\u000b\u000cA \t\n\r\u000b\u000c"), "A");
    assert.equal(trim_ascii(" \u00a0A\u00a0 "), "\u00a0A\u00a0");
    assert.equal(trim_ascii("\u00a0"), "\u00a0")
}
