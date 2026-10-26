#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
check_case() {
 printf '%s\n' "$2" > test_request.json
 actual=$(./run.sh test_request.json)
 if [ "$actual" != "$3" ]; then
  printf 'FAIL %s: %s expected %s\n' "$1" "$actual" "$3"
  exit 1
 fi
 printf 'PASS %s\n' "$1"
}
check_case calc_example '{"op":"calc","expr":"-(2 + 3) * 4 / 3"}' '{"value":-6}'
check_case precedence '{"op":"calc","expr":"2+3*4-10/3"}' '{"value":11}'
check_case associativity '{"op":"calc","expr":"20/3/2-5-1"}' '{"value":-3}'
check_case unary '{"op":"calc","expr":"--+-2 * - - 3"}' '{"value":-6}'
check_case truncation '{"op":"calc","expr":"7/-3"}' '{"value":-2}'
check_case minimum '{"op":"calc","expr":"-2147483648"}' '{"value":-2147483648}'
check_case whitespace '{"op":"calc","expr":"\t(2\n+ 3)\r"}' '{"value":5}'
check_case empty '{"op":"calc","expr":" "}' '{"error":"syntax"}'
check_case operand '{"op":"calc","expr":"2+"}' '{"error":"syntax"}'
check_case parenthesis '{"op":"calc","expr":"(2"}' '{"error":"syntax"}'
check_case extra_parenthesis '{"op":"calc","expr":"2)"}' '{"error":"syntax"}'
check_case implicit '{"op":"calc","expr":"2(3)"}' '{"error":"syntax"}'
check_case trailing '{"op":"calc","expr":"2 3"}' '{"error":"syntax"}'
check_case token '{"op":"calc","expr":"2%3"}' '{"error":"syntax"}'
check_case zero_division '{"op":"calc","expr":"1/(2-2)"}' '{"error":"division_by_zero"}'
check_case ledger_empty '{"op":"ledger","entries":[]}' '{"accounts":[],"accepted":0}'
check_case ledger_dedup '{"op":"ledger","entries":[{"id":"x","account":" z ","amount":2},{"id":"x","account":"","amount":5},{"id":"y","account":"z","amount":-2},{"id":"a","account":"A","amount":4}]}' '{"accounts":[{"account":"A","balance":4,"count":1},{"account":"z","balance":0,"count":2}],"accepted":3}'
check_case empty_account '{"op":"ledger","entries":[{"id":"x","account":"\t\r\n\u000b\u000c ","amount":0}]}' '{"error":"empty_account"}'
check_case escaped_account '{"op":"ledger","entries":[{"id":"a","account":" \"x\\y ","amount":-1},{"id":"b","account":"\u0041","amount":2}]}' '{"accounts":[{"account":"\"x\\y","balance":-1,"count":1},{"account":"A","balance":2,"count":1}],"accepted":2}'
check_case topo_empty '{"op":"topo","nodes":[],"edges":[]}' '{"order":[]}'
check_case topo_order '{"op":"topo","nodes":["z","b","a","c"],"edges":[["a","b"],["a","b"],["b","c"]]}' '{"order":["a","b","c","z"]}'
check_case topo_cycle '{"op":"topo","nodes":["a","b"],"edges":[["a","b"],["b","a"]]}' '{"error":"cycle"}'
check_case self_cycle '{"op":"topo","nodes":["a"],"edges":[["a","a"]]}' '{"error":"cycle"}'
check_case unknown_priority '{"op":"topo","nodes":["a"],"edges":[["a","a"],["z","a"]]}' '{"error":"unknown_node"}'
check_case unknown_op '{"op":"other"}' '{"error":"unknown_op"}'
check_case merge_example '{"op":"merge","intervals":[[4,6],[1,3],[3,4]]}' '{"intervals":[[1,6]]}'
check_case merge_empty '{"op":"merge","intervals":[]}' '{"intervals":[]}'
check_case merge_separated '{"op":"merge","intervals":[[3,4],[1,2]]}' '{"intervals":[[1,2],[3,4]]}'
check_case merge_nested '{"op":"merge","intervals":[[2,3],[1,9],[1,9],[1,2],[5,7]]}' '{"intervals":[[1,9]]}'
check_case merge_points '{"op":"merge","intervals":[[1,1],[0,0],[1,1],[-1,0]]}' '{"intervals":[[-1,0],[1,1]]}'
check_case merge_extremes '{"op":"merge","intervals":[[2147483647,2147483647],[-2147483648,-2147483648],[0,0]]}' '{"intervals":[[-2147483648,-2147483648],[0,0],[2147483647,2147483647]]}'
check_case merge_full_span '{"op":"merge","intervals":[[0,2147483647],[-2147483648,0]]}' '{"intervals":[[-2147483648,2147483647]]}'
check_case merge_invalid '{"op":"merge","intervals":[[1,2],[9,3]]}' '{"error":"invalid_interval"}'
check_case merge_invalid_extremes '{"op":"merge","intervals":[[2147483647,-2147483648]]}' '{"error":"invalid_interval"}'
check_case merge_groups '{"op":"merge","intervals":[[10,12],[2,4],[8,10],[-5,-3],[-3,1],[4,7]]}' '{"intervals":[[-5,1],[2,7],[8,12]]}'
