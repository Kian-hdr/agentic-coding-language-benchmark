package main

import (
	"encoding/json"
	"math/rand"
	"reflect"
	"sort"
	"testing"
)

func TestSelectionAgainstSort(t *testing.T) {
	rng := rand.New(rand.NewSource(291))
	for n := 1; n < 2000; n += 7 {
		for mode := 0; mode < 5; mode++ {
			a := make([]int64, n)
			for i := range a {
				switch mode {
				case 0:
					a[i] = rng.Int63n(9007199254740991)
				case 1:
					a[i] = int64(i)
				case 2:
					a[i] = int64(n - i)
				case 3:
					a[i] = int64(i % 3)
				case 4:
					a[i] = 42
				}
			}
			want := append([]int64(nil), a...)
			sort.Slice(want, func(i, j int) bool { return want[i] < want[j] })
			for _, k := range []int{0, n / 2, n - n/20 - 1, n - 1} {
				if got := selectDuration(append([]int64(nil), a...), k); got != want[k] {
					t.Fatalf("n=%d mode=%d k=%d got=%d want=%d", n, mode, k, got, want[k])
				}
			}
		}
	}
}

func TestReusedProcessorMatchesLegacy(t *testing.T) {
	inputs := []string{
		`{"op":"invoice","events":[{"id":"a","customer":" X ","amount_cents":45,"status":"paid"}]}`,
		`{"op":"invoice","events":[{},{}]}`,
		`{"op":"invoice","events":null}`,
		`{"op":"telemetry","samples":[-3,8,90,-45],"window":2,"threshold":2}`,
		`{"op":"telemetry","samples":[0],"window":1}`,
		`{"op":"telemetry","samples":null,"window":1}`,
		`{"op":"access_log","start_ms":0,"end_ms":9,"events":[{"ts_ms":1,"route":" /x ","status":503,"duration_us":23,"bytes":4}]}`,
		`{"op":"access_log","start_ms":0,"end_ms":9,"events":[{}]}`,
		`{"op":"invoice","samples":"ignored","events":[]}`,
		`{"op":"unknown","samples":"ignored"}`,
		`{"op":"invoice","op":"telemetry","samples":[4],"window":1}`,
		`{"op":"invoice","events":[],"events":null}`,
		`{"op":"invoice","events":[{"amount_cents":"bad"}]}`,
		`{"op":"access_log","events":[{"route":"bad","duration_us":"bad"}]}`,
		`null`, `[]`, `123`, `{"op":`,
	}
	p := processor{}
	for repeat := 0; repeat < 3; repeat++ {
		for _, input := range inputs {
			got, _ := json.Marshal(p.process([]byte(input)))
			want, _ := json.Marshal(processLegacy([]byte(input)))
			if !reflect.DeepEqual(got, want) {
				t.Fatalf("%s: got %s want %s", input, got, want)
			}
		}
	}
}

func BenchmarkProcessing(b *testing.B) {
	events := make([]invoiceEvent, 800)
	accesses := make([]accessEvent, 800)
	samples := make([]int64, 8000)
	rng := rand.New(rand.NewSource(145))
	for i := range events {
		events[i] = invoiceEvent{ID: string(rune(33 + i)), Customer: string(rune(33 + i%20)), Amount: int64(i), Status: "paid"}
		accesses[i] = accessEvent{TS: 1, Route: string(rune(33 + i%8)), Status: 200, Duration: rng.Int63n(100000), Bytes: 100}
	}
	for i := range samples {
		samples[i] = int64(i%151) - 75
	}
	requests := []any{
		map[string]any{"op": "invoice", "events": events},
		map[string]any{"op": "access_log", "start_ms": 0, "end_ms": 2, "events": accesses},
		map[string]any{"op": "telemetry", "samples": samples, "window": 19, "threshold": 3},
	}
	for i, name := range []string{"invoice", "access_log", "telemetry"} {
		data, _ := json.Marshal(requests[i])
		b.Run(name+"/legacy", func(b *testing.B) {
			b.ReportAllocs()
			for j := 0; j < b.N; j++ {
				processLegacy(data)
			}
		})
		b.Run(name+"/optimized", func(b *testing.B) {
			p := processor{}
			b.ReportAllocs()
			for j := 0; j < b.N; j++ {
				p.process(data)
			}
		})
	}
}
