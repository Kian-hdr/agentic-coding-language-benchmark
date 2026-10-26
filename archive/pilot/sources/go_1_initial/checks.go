//go:build localchecks

package main

import (
	"encoding/json"
	"fmt"
	"os"
)

type checker struct{ count int }

func (t *checker) Helper()        {}
func (t *checker) Fatal(v ...any) { fmt.Fprintln(os.Stderr, v...); os.Exit(1) }
func (t *checker) Fatalf(format string, v ...any) {
	fmt.Fprintf(os.Stderr, format+"\n", v...)
	os.Exit(1)
}
func (t *checker) Run(name string, f func(*checker)) { t.count++; f(t) }
func init() {
	t := &checker{}
	TestOperations(t)
	TestCalc(t)
	fmt.Printf("Passed %d local checks\n", t.count)
	os.Exit(0)
}

func TestOperations(t *checker) {
	cases := []struct{ name, input, want string }{
		{"unknown", `{"op":"other"}`, `{"error":"unknown_op"}`},
		{"ledger_empty", `{"op":"ledger","entries":[]}`, `{"accounts":[],"accepted":0}`},
		{"ledger_first_wins", `{"op":"ledger","entries":[{"id":"a","account":" bank ","amount":5},{"id":"a","account":"","amount":99},{"id":"b","account":"bank","amount":-5},{"id":"c","account":"\tA\r\n\u000b\f","amount":2}]}`, `{"accounts":[{"account":"A","balance":2,"count":1},{"account":"bank","balance":0,"count":2}],"accepted":3}`},
		{"ledger_empty_account", `{"op":"ledger","entries":[{"id":"a","account":" \t\r\n\u000b\f","amount":5}]}`, `{"error":"empty_account"}`},
		{"ledger_non_ascii_space", `{"op":"ledger","entries":[{"id":"a","account":"\u00a0","amount":5}]}`, `{"accounts":[{"account":"\u00a0","balance":5,"count":1}],"accepted":1}`},
		{"topo_empty", `{"op":"topo","nodes":[],"edges":[]}`, `{"order":[]}`},
		{"topo_dynamic_priority", `{"op":"topo","nodes":["z","b","a","c"],"edges":[["a","b"],["a","b"]]}`, `{"order":["a","b","c","z"]}`},
		{"topo_cycle", `{"op":"topo","nodes":["a","b"],"edges":[["a","b"],["b","a"]]}`, `{"error":"cycle"}`},
		{"topo_self", `{"op":"topo","nodes":["a"],"edges":[["a","a"]]}`, `{"error":"cycle"}`},
		{"topo_unknown_before_cycle", `{"op":"topo","nodes":["a"],"edges":[["a","a"],["a","x"]]}`, `{"error":"unknown_node"}`},
		{"topo_unknown_source", `{"op":"topo","nodes":["a"],"edges":[["x","a"]]}`, `{"error":"unknown_node"}`},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *checker) {
			var r request
			if err := json.Unmarshal([]byte(c.input), &r); err != nil {
				t.Fatal(err)
			}
			check(t, execute(r), c.want)
		})
	}
}
func check(t *checker, got any, want string) {
	t.Helper()
	b, err := json.Marshal(got)
	if err != nil {
		t.Fatal(err)
	}
	var actual, expected any
	if err = json.Unmarshal(b, &actual); err != nil {
		t.Fatal(err)
	}
	if err = json.Unmarshal([]byte(want), &expected); err != nil {
		t.Fatal(err)
	}
	a, _ := json.Marshal(actual)
	e, _ := json.Marshal(expected)
	if string(a) != string(e) {
		t.Fatalf("got %s, want %s", b, want)
	}
}
func TestCalc(t *checker) {
	cases := []struct{ expr, want string }{
		{"-(2 + 3) * 4 / 3", `{"value":-6}`},
		{"2+3*4", `{"value":14}`},
		{"20/3/2", `{"value":3}`},
		{"8-3-2", `{"value":3}`},
		{"7/-3", `{"value":-2}`},
		{"-7/-3", `{"value":2}`},
		{"--+-+2", `{"value":-2}`},
		{"1--2", `{"value":3}`},
		{" \t\n\r\v\f(00012 + +3) ", `{"value":15}`},
		{"-2147483648", `{"value":-2147483648}`},
		{"2147483647", `{"value":2147483647}`},
		{"1/(2-2)", `{"error":"division_by_zero"}`},
		{"", `{"error":"syntax"}`},
		{" \t", `{"error":"syntax"}`},
		{"()", `{"error":"syntax"}`},
		{"1+", `{"error":"syntax"}`},
		{"*1", `{"error":"syntax"}`},
		{"(1", `{"error":"syntax"}`},
		{"1)", `{"error":"syntax"}`},
		{"1 2", `{"error":"syntax"}`},
		{"2(3)", `{"error":"syntax"}`},
		{"(2)3", `{"error":"syntax"}`},
		{"2**3", `{"error":"syntax"}`},
		{"2.5", `{"error":"syntax"}`},
		{"1e2", `{"error":"syntax"}`},
		{"x", `{"error":"syntax"}`},
		{"1\u00a0+2", `{"error":"syntax"}`},
	}
	for _, c := range cases {
		t.Run(c.expr, func(t *checker) { check(t, calc(c.expr), c.want) })
	}
}
