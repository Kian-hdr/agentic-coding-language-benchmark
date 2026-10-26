package main

import (
	"encoding/json"
	"testing"
)

func TestInvoiceFees(t *testing.T) {
	events := `"events":[{"id":"a","customer":" A ","amount_cents":5,"status":"paid"},{"id":"b","customer":"A","amount_cents":5,"status":"paid"},{"id":"a","customer":"B","amount_cents":100,"status":"paid"},{"id":"c","customer":"B","amount_cents":20,"status":"refund"},{"id":"d","customer":"B","amount_cents":10,"status":"pending"},{"id":"e","customer":" ","amount_cents":10,"status":"paid"}]`
	checkJSON(t, `{"op":"invoice","fee_bps":1000,`+events+`}`, `{"customers":[{"customer":"A","gross_cents":10,"refund_cents":0,"fee_cents":2,"net_cents":8,"count":2},{"customer":"B","gross_cents":0,"refund_cents":20,"fee_cents":0,"net_cents":-20,"count":1}],"accepted":3,"duplicates":1,"ignored":1,"rejected":1,"gross_cents":10,"refund_cents":20,"fee_cents":2,"net_cents":-12}`)
	checkJSON(t, `{"op":"invoice","fee_bps":0,`+events+`}`, `{"customers":[{"customer":"A","gross_cents":10,"refund_cents":0,"fee_cents":0,"net_cents":10,"count":2},{"customer":"B","gross_cents":0,"refund_cents":20,"fee_cents":0,"net_cents":-20,"count":1}],"accepted":3,"duplicates":1,"ignored":1,"rejected":1,"gross_cents":10,"refund_cents":20,"fee_cents":0,"net_cents":-10}`)
	checkJSON(t, `{"op":"invoice","fee_bps":1,"events":[{"id":"a","customer":"A","amount_cents":9007199254735991,"status":"paid"}]}`, `{"customers":[{"customer":"A","gross_cents":9007199254735991,"refund_cents":0,"fee_cents":900719925474,"net_cents":9006298534810517,"count":1}],"accepted":1,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":9007199254735991,"refund_cents":0,"fee_cents":900719925474,"net_cents":9006298534810517}`)
	for _, input := range []string{`{"op":"invoice","fee_bps":0}`, `{"op":"invoice","fee_bps":1000,"events":null}`} {
		checkJSON(t, input, `{"customers":[],"accepted":0,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":0,"refund_cents":0,"net_cents":0,"fee_cents":0}`)
	}
}

func TestFeeRecoveryAndIsolation(t *testing.T) {
	p := processor{}
	legacy := `{"op":"invoice","events":[{"id":"a","customer":"A","amount_cents":49,"status":"paid"}]}`
	wantLegacy := `{"customers":[{"customer":"A","gross_cents":49,"refund_cents":0,"net_cents":49,"count":1}],"accepted":1,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":49,"refund_cents":0,"net_cents":49}`
	inputs := []string{
		legacy,
		`{"op":"invoice","fee_bps":100,"events":[{"id":"a","customer":"A","amount_cents":49,"status":"paid"},{"id":"b","customer":"A","amount_cents":50,"status":"paid"}]}`,
		`{"op":"invoice","fee_bps":0,"events":[{"customer":"B","amount_cents":"bad"}]}`,
		`{"op":"invoice","fee_bps":100,"samples":"ignored","events":[{"id":"x","customer":"X","amount_cents":150,"status":"paid"}]}`,
		`{"op":"access_log","fee_bps":"ignored","events":[]}`,
		`{"op":"telemetry","fee_bps":null,"samples":[3],"window":1}`,
		`{"op":"invoice","fee_bps":0,"events":[]}`,
		`{"op":`,
		legacy,
	}
	wants := []string{
		wantLegacy,
		`{"customers":[{"customer":"A","gross_cents":99,"refund_cents":0,"net_cents":98,"count":2,"fee_cents":1}],"accepted":2,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":99,"refund_cents":0,"net_cents":98,"fee_cents":1}`,
		`{"error":"invalid_json"}`,
		`{"customers":[{"customer":"X","gross_cents":150,"refund_cents":0,"net_cents":148,"count":1,"fee_cents":2}],"accepted":1,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":150,"refund_cents":0,"net_cents":148,"fee_cents":2}`,
		`{"routes":[],"total_count":0,"total_errors":0,"total_bytes":0}`,
		`{"count":1,"min":3,"max":3,"above":1,"weighted_checksum":3}`,
		`{"customers":[],"accepted":0,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":0,"refund_cents":0,"net_cents":0,"fee_cents":0}`,
		`{"error":"invalid_json"}`,
		wantLegacy,
	}
	for repeat := 0; repeat < 3; repeat++ {
		for i, input := range inputs {
			checkJSON(t, input, wants[i])
			got, err := json.Marshal(p.process([]byte(input)))
			if err != nil {
				t.Fatal(err)
			}
			want, _ := json.Marshal(process([]byte(input)))
			if string(got) != string(want) {
				t.Fatalf("reused processor: %s: got %s want %s", input, got, want)
			}
		}
	}
	for _, fee := range []string{`-1`, `1001`, `1.5`, `"100"`, `null`, `true`, `{}`} {
		checkJSON(t, `{"op":"invoice","fee_bps":`+fee+`}`, `{"error":"invalid_json"}`)
	}
}
