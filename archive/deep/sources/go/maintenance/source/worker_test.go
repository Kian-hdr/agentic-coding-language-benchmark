package main

import (
	"bytes"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
)

func TestPrebuiltWorkerFromOtherDirectory(t *testing.T) {
	root, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	dir := t.TempDir()
	input := filepath.Join(dir, "input with spaces.jsonl")
	output := filepath.Join(dir, "output with spaces.jsonl")
	requests := [][]byte{
		[]byte(`{"op":"invoice","fee_bps":1000,"events":[{"id":"a","customer":"A","amount_cents":5,"status":"paid"},{"id":"b","customer":"A","amount_cents":5,"status":"paid"}]}`),
		[]byte(`{"op":"invoice","fee_bps":0,"events":[{"id":"a","customer":"A","amount_cents":50,"status":"refund"}]}`),
		[]byte(`{"op":"invoice","fee_bps":100,"events":[{"amount_cents":"bad"}]}`),
		[]byte(`{"op":"invoice","events":[{"id":"a","customer":" A ","amount_cents":9007199254740991,"status":"paid"}]}`),
		[]byte(`{"op":"access_log","start_ms":-1,"end_ms":1,"events":[{"ts_ms":0,"route":" / ","status":500,"duration_us":9007199254740991,"bytes":9007199254740991}]}`),
		[]byte(`{"op":"telemetry","samples":[-5,0,8],"window":2,"threshold":0}`),
		[]byte(`{"op":"unknown"}`),
		[]byte(`not-json`),
	}
	var in, want bytes.Buffer
	for i := 0; i < 500; i++ {
		request := requests[i%len(requests)]
		in.Write(request)
		if i != 499 {
			in.WriteString("\r\n\n")
		}
		if err := json.NewEncoder(&want).Encode(process(request)); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.WriteFile(input, in.Bytes(), 0600); err != nil {
		t.Fatal(err)
	}
	cmd := exec.Command(filepath.Join(root, "worker.sh"), input, output)
	cmd.Dir = dir
	if diagnostic, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("worker: %v: %s", err, diagnostic)
	}
	got, err := os.ReadFile(output)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, want.Bytes()) {
		t.Fatal("worker output differs from expected 500 responses")
	}
}
