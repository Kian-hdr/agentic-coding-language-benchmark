//go:build localtests

package main

import (
	"encoding/json"
	"fmt"
	"os"
)

// This standalone harness avoids the unavailable testing package in this toolchain.
type testCase struct{ name string }

var testCount int

func (t *testCase) Fatal(args ...any) {
	fmt.Fprintln(os.Stderr, append([]any{t.name + ":"}, args...)...)
	os.Exit(1)
}
func (t *testCase) Fatalf(format string, args ...any)  { t.Fatal(fmt.Sprintf(format, args...)) }
func (t *testCase) Run(name string, f func(*testCase)) { f(&testCase{name: name}); testCount++ }
func init() {
	t := &testCase{name: "root"}
	TestOperations(t)
	TestHeap(t)
	fmt.Printf("Passed %d operation cases and heap ordering test\n", testCount)
	os.Exit(0)
}
func TestOperations(t *testCase) {
	cases := []struct{ name, request, want string }{
		{"unknown", `{"op":"other"}`, `{"error":"unknown_op"}`},
		{"ledger_empty", `{"op":"ledger","entries":[]}`, `{"accounts":[],"accepted":0}`},
		{"ledger_example", `{"op":"ledger","entries":[{"id":"a","account":" bank ","amount":5}]}`, `{"accounts":[{"account":"bank","balance":5,"count":1}],"accepted":1}`},
		{"ledger_duplicates_and_sort", `{"op":"ledger","entries":[{"id":"a","account":" z ","amount":5},{"id":"a","account":"","amount":99},{"id":"b","account":"A","amount":-2},{"id":"c","account":"z","amount":-5},{"id":"d","account":"a","amount":0}]}`, `{"accounts":[{"account":"A","balance":-2,"count":1},{"account":"a","balance":0,"count":1},{"account":"z","balance":0,"count":2}],"accepted":4}`},
		{"ledger_ascii_space", `{"op":"ledger","entries":[{"id":"a","account":"\t\r\n\u000b\f bank \t","amount":5}]}`, `{"accounts":[{"account":"bank","balance":5,"count":1}],"accepted":1}`},
		{"ledger_nonascii_space", `{"op":"ledger","entries":[{"id":"a","account":"\u00a0","amount":1}]}`, `{"accounts":[{"account":"\u00a0","balance":1,"count":1}],"accepted":1}`},
		{"ledger_empty_account", `{"op":"ledger","entries":[{"id":"a","account":" \n\t","amount":0}]}`, `{"error":"empty_account"}`},
		{"topo_empty", `{"op":"topo","nodes":[],"edges":[]}`, `{"order":[]}`},
		{"topo_example", `{"op":"topo","nodes":["b","a"],"edges":[["a","b"]]}`, `{"order":["a","b"]}`},
		{"topo_dynamic_choice", `{"op":"topo","nodes":["z","b","a","c"],"edges":[["b","a"],["b","a"]]}`, `{"order":["b","a","c","z"]}`},
		{"topo_ascii", `{"op":"topo","nodes":["a","B","A","aa"],"edges":[]}`, `{"order":["A","B","a","aa"]}`},
		{"topo_cycle", `{"op":"topo","nodes":["a","b"],"edges":[["a","b"],["b","a"]]}`, `{"error":"cycle"}`},
		{"topo_self", `{"op":"topo","nodes":["a"],"edges":[["a","a"]]}`, `{"error":"cycle"}`},
		{"topo_unknown_over_cycle", `{"op":"topo","nodes":["a"],"edges":[["a","a"],["a","b"]]}`, `{"error":"unknown_node"}`},
		{"topo_unknown_source", `{"op":"topo","nodes":["a"],"edges":[["b","a"]]}`, `{"error":"unknown_node"}`},
		{"calc_example", `{"op":"calc","expr":"-(2 + 3) * 4 / 3"}`, `{"value":-6}`},
		{"calc_precedence", `{"op":"calc","expr":"2+3*4-8/3"}`, `{"value":12}`},
		{"calc_left_division", `{"op":"calc","expr":"20/3/2"}`, `{"value":3}`},
		{"calc_left_subtraction", `{"op":"calc","expr":"10-3-2"}`, `{"value":5}`},
		{"calc_negative_divisor", `{"op":"calc","expr":"7/-3"}`, `{"value":-2}`},
		{"calc_double_negative", `{"op":"calc","expr":"-7/-3"}`, `{"value":2}`},
		{"calc_signs", `{"op":"calc","expr":"- + - -- (2 + +3)"}`, `{"value":5}`},
		{"calc_binary_unary", `{"op":"calc","expr":"1--2*+-3"}`, `{"value":-5}`},
		{"calc_spaces", `{"op":"calc","expr":"\t\r\n\u000b\f (00012) "}`, `{"value":12}`},
		{"calc_min", `{"op":"calc","expr":"-2147483648"}`, `{"value":-2147483648}`},
		{"calc_max", `{"op":"calc","expr":"2147483647"}`, `{"value":2147483647}`},
		{"calc_zero_division", `{"op":"calc","expr":"1/(3-3)"}`, `{"error":"division_by_zero"}`},
		{"calc_nested", `{"op":"calc","expr":"((2+3)*(7-2))/(-2)"}`, `{"value":-12}`},
	}
	for _, expr := range []string{"", " ", "()", "1+", "*1", "1 2", "2(3)", "(2)3", "(2)(3)", "1)", "(1", "abc", "1.2", "1e3", "0x10", "1%2", "1//2", "--", "1+()", "1\u00a0+2", "[1]", "2**3", "((1)"} {
		input, _ := json.Marshal(Request{Op: "calc", Expr: expr})
		cases = append(cases, struct{ name, request, want string }{"syntax_" + expr, string(input), `{"error":"syntax"}`})
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testCase) {
			var r Request
			if err := json.Unmarshal([]byte(tc.request), &r); err != nil {
				t.Fatal(err)
			}
			actual, err := json.Marshal(evaluate(r))
			if err != nil {
				t.Fatal(err)
			}
			var want, got any
			if err := json.Unmarshal([]byte(tc.want), &want); err != nil {
				t.Fatal(err)
			}
			if err := json.Unmarshal(actual, &got); err != nil {
				t.Fatal(err)
			}
			canonicalWant, _ := json.Marshal(want)
			canonicalGot, _ := json.Marshal(got)
			if string(canonicalWant) != string(canonicalGot) {
				t.Fatalf("got %s; want %s", actual, tc.want)
			}
		})
	}
}

func TestHeap(t *testCase) {
	h := &stringHeap{}
	for _, value := range []string{"z", "b", "a", "d", "c", "aa", "A", "0", "zz", "x", "y"} {
		h.Push(value)
	}
	previous := ""
	for h.Len() > 0 {
		value := h.Pop()
		if value < previous {
			t.Fatalf("heap returned %q after %q", value, previous)
		}
		previous = value
	}
}
