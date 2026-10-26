package main

import (
	"encoding/json"
	"math/rand"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"testing"
)

func checkJSON(t *testing.T, input, expected string) {
	t.Helper()
	actual, err := json.Marshal(process([]byte(input)))
	if err != nil {
		t.Fatal(err)
	}
	var a, b any
	if err = json.Unmarshal(actual, &a); err != nil {
		t.Fatal(err)
	}
	if err = json.Unmarshal([]byte(expected), &b); err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(a, b) {
		t.Fatalf("input %s\ngot %s\nwant %s", input, actual, expected)
	}
}
func TestExamplesAndErrors(t *testing.T) {
	cases := [][2]string{
		{`{"op":"invoice","events":[{"id":"e1","customer":" A ","amount_cents":150,"status":"paid"}]}`, `{"customers":[{"customer":"A","gross_cents":150,"refund_cents":0,"net_cents":150,"count":1}],"accepted":1,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":150,"refund_cents":0,"net_cents":150}`},
		{`{"op":"access_log","start_ms":100,"end_ms":200,"events":[{"ts_ms":120,"route":" /api/orders ","status":503,"duration_us":1234,"bytes":20}]}`, `{"routes":[{"route":"/api/orders","count":1,"errors":1,"total_bytes":20,"max_us":1234,"p95_us":1234}],"total_count":1,"total_errors":1,"total_bytes":20}`},
		{`{"op":"telemetry","samples":[-2,5,8,1],"window":2,"threshold":3}`, `{"count":3,"min":1,"max":6,"above":2,"weighted_checksum":25}`},
		{`{"op":"telemetry","samples":[-8,1],"window":2,"threshold":-3}`, `{"count":1,"min":-3,"max":-3,"above":0,"weighted_checksum":-3}`},
		{`{"op":"telemetry","samples":[9007199254740991],"window":1,"threshold":0}`, `{"count":1,"min":9007199254740991,"max":9007199254740991,"above":1,"weighted_checksum":9007199254740991}`},
		{`{"op":"telemetry","samples":[],"window":1}`, `{"error":"invalid_window"}`},
		{`{"op":"telemetry","samples":[1],"window":0}`, `{"error":"invalid_window"}`},
		{`{"op":"telemetry","samples":[1],"window":-1}`, `{"error":"invalid_window"}`},
		{`{"op":"invoice","events":[]}`, `{"customers":[],"accepted":0,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":0,"refund_cents":0,"net_cents":0}`},
		{`{"op":"access_log","start_ms":2,"end_ms":1,"events":[]}`, `{"routes":[],"total_count":0,"total_errors":0,"total_bytes":0}`},
		{`{"op":"nope"}`, `{"error":"unknown_op"}`},
		{`{"op":`, `{"error":"invalid_json"}`},
		{`{} {}`, `{"error":"invalid_json"}`},
	}
	for _, c := range cases {
		checkJSON(t, c[0], c[1])
	}
}
func TestInvoiceRules(t *testing.T) {
	events := []invoiceEvent{
		{"a", "\v\f \t\r\n", 1, "paid"},
		{"a", "A", 10, "paid"},
		{"b", "A", -1, "pending"},
		{"c", "A", 1, "invalid"},
		{"d", "A", 1, "pending"},
		{"e", "A", 1, "void"},
		{"f", " Z ", 5000000000, "paid"},
		{"g", "Z", 5000000000, "refund"},
		{"h", "AA", 0, "paid"},
		{"i", "A", 1, "refund"},
	}
	got := invoice(events)
	want := invoiceResult{Customers: []customerRow{{"A", 0, 1, -1, 1}, {"AA", 0, 0, 0, 1}, {"Z", 5000000000, 5000000000, 0, 2}}, Accepted: 4, Duplicates: 1, Ignored: 2, Rejected: 3, Gross: 5000000000, Refund: 5000000001, Net: -1}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("got %+v want %+v", got, want)
	}
}
func TestTelemetryRandom(t *testing.T) {
	rng := rand.New(rand.NewSource(79))
	for iter := 0; iter < 1500; iter++ {
		n := 1 + rng.Intn(100)
		samples := make([]int64, n)
		for i := range samples {
			samples[i] = rng.Int63n(20000000000) - 10000000000
		}
		w := 1 + rng.Intn(n)
		threshold := rng.Int63n(20000000000) - 10000000000
		want := telemetryResult{}
		for i := 0; i+w <= n; i++ {
			var sum int64
			for _, v := range samples[i : i+w] {
				sum += v
			}
			avg := sum / int64(w)
			if i == 0 || avg < want.Min {
				want.Min = avg
			}
			if i == 0 || avg > want.Max {
				want.Max = avg
			}
			want.Count++
			if avg > threshold {
				want.Above++
			}
			want.Checksum += int64(i+1) * avg
		}
		if got := telemetry(samples, int64(w), threshold); !reflect.DeepEqual(got, want) {
			t.Fatalf("iteration %d: got %+v want %+v", iter, got, want)
		}
	}
}
func TestAccessRandom(t *testing.T) {
	rng := rand.New(rand.NewSource(23))
	for iter := 0; iter < 200; iter++ {
		events := make([]accessEvent, 200)
		for i := range events {
			events[i] = accessEvent{int64(rng.Intn(30)), []string{" /Z ", " /AA ", " /A ", " \v\f "}[rng.Intn(4)], int64(499 + rng.Intn(4)), rng.Int63n(9000000000), rng.Int63n(9000000000)}
		}
		got := accessLog(10, 20, events)
		want := accessResult{Routes: []routeRow{}}
		for _, route := range []string{"", "/A", "/AA", "/Z"} {
			row := routeRow{Route: route}
			ds := []int64{}
			for _, e := range events {
				if e.TS < 10 || e.TS >= 20 || strings.Trim(e.Route, asciiSpace) != route {
					continue
				}
				row.Count++
				if e.Status >= 500 {
					row.Errors++
				}
				row.TotalBytes += e.Bytes
				ds = append(ds, e.Duration)
			}
			if len(ds) == 0 {
				continue
			}
			sort.Slice(ds, func(i, j int) bool { return ds[i] < ds[j] })
			row.Max = ds[len(ds)-1]
			// Reference rank by counting the first rank that reaches 95 percent.
			for rank := 1; rank <= len(ds); rank++ {
				if rank*100 >= len(ds)*95 {
					row.P95 = ds[rank-1]
					break
				}
			}
			want.Routes = append(want.Routes, row)
			want.Count += row.Count
			want.Errors += row.Errors
			want.Bytes += row.TotalBytes
		}
		if !reflect.DeepEqual(got, want) {
			t.Fatalf("iteration %d: got %+v want %+v", iter, got, want)
		}
	}
}
func TestBulkFile(t *testing.T) {
	dir := t.TempDir()
	input := filepath.Join(dir, "in.jsonl")
	output := filepath.Join(dir, "out.jsonl")
	a := `{"op":"telemetry","samples":[1,2,3],"window":2,"threshold":1}`
	large := `{"op":"invoice","events":[],"padding":"` + strings.Repeat("x", 150000) + `"}`
	content := "\r\n" + a + "\r\n{broken\n\t \n" + large + "\n" + a
	if err := os.WriteFile(input, []byte(content), 0600); err != nil {
		t.Fatal(err)
	}
	if err := run(input, output); err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(output)
	if err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimSuffix(string(data), "\n"), "\n")
	if len(lines) != 4 || lines[0] != lines[3] || lines[1] != `{"error":"invalid_json"}` {
		t.Fatalf("bad bulk output: %v", lines)
	}
	for _, line := range lines {
		if !json.Valid([]byte(line)) {
			t.Fatalf("invalid output: %s", line)
		}
	}
	if err := run(input, input); err == nil {
		t.Fatal("expected same-file error")
	}
	original, err := os.ReadFile(input)
	if err != nil || string(original) != content {
		t.Fatal("same-file check changed input")
	}
}

func TestAccessBoundaries(t *testing.T) {
	events := []accessEvent{{9, " /X ", 500, 1000, 1}, {20, " /X ", 500, 1000, 1}}
	for i := 1; i <= 20; i++ {
		events = append(events, accessEvent{10, " /X ", 499, int64(i), 5000000000})
	}
	got := accessLog(10, 20, events)
	want := accessResult{Routes: []routeRow{{"/X", 20, 0, 100000000000, 20, 19}}, Count: 20, Bytes: 100000000000}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("got %+v want %+v", got, want)
	}
	events = append(events, accessEvent{19, " /X ", 500, 21, 1})
	got = accessLog(10, 20, events)
	if got.Routes[0].P95 != 20 || got.Errors != 1 || got.Count != 21 {
		t.Fatalf("bad 21-event rank: %+v", got)
	}
}
