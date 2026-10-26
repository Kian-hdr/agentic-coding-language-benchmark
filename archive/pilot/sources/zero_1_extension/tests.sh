#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
count=0
case_test() {
 printf '%s\n' "$1" > test_request.json
 actual=$(./run.sh test_request.json)
 if [ "$actual" != "$2" ]; then
  printf 'FAIL: %s\nexpected: %s\nactual: %s\n' "$1" "$2" "$actual" >&2
  exit 1
 fi
 count=$((count + 1))
}
case_test '{"op":"other"}' '{"error":"unknown_op"}'
case_test '{"op":"ledger","entries":[]}' '{"accounts":[],"accepted":0}'
case_test '{"op":"ledger","entries":[{"id":"a","account":" \t\r\n\u000b\u000c","amount":1}]}' '{"error":"empty_account"}'
case_test '{"op":"ledger","entries":[{"id":"a","account":" bank ","amount":5},{"id":"a","account":" ","amount":900},{"id":"b","account":"bank","amount":-5},{"id":"c","account":"apple","amount":-2}]}' '{"accounts":[{"account":"apple","balance":-2,"count":1},{"account":"bank","balance":0,"count":2}],"accepted":3}'
case_test '{"op":"ledger","entries":[{"id":"\u0061","account":"x\"y","amount":-2147483648},{"id":"a","account":"bad","amount":2},{"id":"b","account":" A ","amount":2147483647}]}' '{"accounts":[{"account":"A","balance":2147483647,"count":1},{"account":"x\"y","balance":-2147483648,"count":1}],"accepted":2}'
case_test '{"op":"topo","nodes":[],"edges":[]}' '{"order":[]}'
case_test '{"op":"topo","nodes":["z","b","a","c"],"edges":[["a","b"],["a","b"],["b","c"]]}' '{"order":["a","b","c","z"]}'
case_test '{"op":"topo","nodes":["a","b"],"edges":[["a","b"],["b","a"]]}' '{"error":"cycle"}'
case_test '{"op":"topo","nodes":["a"],"edges":[["a","a"]]}' '{"error":"cycle"}'
case_test '{"op":"topo","nodes":["a"],"edges":[["a","a"],["a","missing"]]}' '{"error":"unknown_node"}'
case_test '{"op":"topo","nodes":["b","a"],"edges":[["b","a"]]}' '{"order":["b","a"]}'
case_test '{"op":"topo","nodes":["b","\u0061"],"edges":[["a","b"]]}' '{"order":["\u0061","b"]}'
case_test '{"op":"calc","expr":"-(2 + 3) * 4 / 3"}' '{"value":-6}'
case_test '{"op":"calc","expr":"1+2*3"}' '{"value":7}'
case_test '{"op":"calc","expr":"20/3/2"}' '{"value":3}'
case_test '{"op":"calc","expr":"10-3-2"}' '{"value":5}'
case_test '{"op":"calc","expr":"-7/3"}' '{"value":-2}'
case_test '{"op":"calc","expr":"7/-3"}' '{"value":-2}'
case_test '{"op":"calc","expr":"---++5 + 2*-(-3)"}' '{"value":1}'
case_test '{"op":"calc","expr":"-((2+3))*--2"}' '{"value":-10}'
case_test '{"op":"calc","expr":"\t 00012\u000b +\f3\r\n"}' '{"value":15}'
case_test '{"op":"calc","expr":"-2147483648"}' '{"value":-2147483648}'
case_test '{"op":"calc","expr":"2147483647-2147483647"}' '{"value":0}'
case_test '{"op":"calc","expr":"1/(2-2)"}' '{"error":"division_by_zero"}'
case_test '{"op":"calc","expr":""}' '{"error":"syntax"}'
case_test '{"op":"calc","expr":"  "}' '{"error":"syntax"}'
case_test '{"op":"calc","expr":"()"}' '{"error":"syntax"}'
case_test '{"op":"calc","expr":"1+"}' '{"error":"syntax"}'
case_test '{"op":"calc","expr":"(1+2"}' '{"error":"syntax"}'
case_test '{"op":"calc","expr":"1+2)"}' '{"error":"syntax"}'
case_test '{"op":"calc","expr":"1 2"}' '{"error":"syntax"}'
case_test '{"op":"calc","expr":"2(3)"}' '{"error":"syntax"}'
case_test '{"op":"calc","expr":"(2)3"}' '{"error":"syntax"}'
case_test '{"op":"calc","expr":"2**3"}' '{"error":"syntax"}'
case_test '{"op":"calc","expr":"1.2"}' '{"error":"syntax"}'
case_test '{"op":"calc","expr":"x"}' '{"error":"syntax"}'
case_test '{"op":"merge","intervals":[[4,6],[1,3],[3,4]]}' '{"intervals":[[1,6]]}'
case_test '{"op":"merge","intervals":[]}' '{"intervals":[]}'
case_test '{"op":"merge","intervals":[[1,2],[3,4]]}' '{"intervals":[[1,2],[3,4]]}'
case_test '{"op":"merge","intervals":[[8,9],[1,10],[1,2],[3,4],[1,10]]}' '{"intervals":[[1,10]]}'
case_test '{"op":"merge","intervals":[[5,5],[0,0],[-3,-1],[-1,0],[5,5]]}' '{"intervals":[[-3,0],[5,5]]}'
case_test '{"op":"merge","intervals":[[2,1]]}' '{"error":"invalid_interval"}'
case_test '{"op":"merge","intervals":[[1,8],[9,10],[7,3]]}' '{"error":"invalid_interval"}'
case_test '{"op":"merge","intervals":[[-2147483648,-2147483648],[2147483647,2147483647]]}' '{"intervals":[[-2147483648,-2147483648],[2147483647,2147483647]]}'
case_test '{"op":"merge","intervals":[[2147483647,2147483647],[-2147483648,2147483647]]}' '{"intervals":[[-2147483648,2147483647]]}'
case_test '{"op":"merge","intervals":[[4,6],[1,2],[2,3],[8,9],[6,7]]}' '{"intervals":[[1,3],[4,7],[8,9]]}'
printf '%s tests passed\n' "$count"
