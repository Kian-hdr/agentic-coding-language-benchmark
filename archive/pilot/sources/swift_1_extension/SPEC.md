
### ledger
Input: {"op":"ledger","entries":[{"id":"a","account":" bank ","amount":5}, ...]}.
Process entries in order; the first occurrence of an id wins and all later
occurrences are ignored, even if their fields differ. Trim ASCII whitespace
from account names. If an accepted entry has an empty account, return
{"error":"empty_account"}. Group accepted entries by normalized account.
Output {"accounts":[{"account":"bank","balance":5,"count":1}],"accepted":1}.
Sort accounts by ascending ASCII name. Retain zero-balance accounts. Empty
input produces {"accounts":[],"accepted":0}. All input fields have the stated
types; ids are nonempty ASCII; amounts and their sums fit signed 32-bit.

### topo
Input: {"op":"topo","nodes":["a","b"],"edges":[["a","b"]]}.
Nodes are distinct ASCII identifiers. Deduplicate edges. An edge with any
endpoint absent from nodes returns {"error":"unknown_node"}, even if a cycle
also exists. Otherwise, repeatedly choose the lexicographically smallest
currently available node to form a topological ordering.
Output {"order":["a","b"]}; if impossible output {"error":"cycle"}.
Empty graph returns {"order":[]}. Self-edges are cycles.

### calc
Input: {"op":"calc","expr":"-(2 + 3) * 4 / 3"}.
Evaluate decimal nonnegative integer literals, ASCII whitespace, parentheses,
unary + and -, and binary + - * /. Use conventional precedence, left-associative
binary operations, and division truncating toward zero. Unary signs may repeat.
Output {"value":-6}. Reject other tokens, missing operands, unmatched parentheses,
empty expressions, implicit multiplication, and trailing tokens with
{"error":"syntax"}. Division by zero returns {"error":"division_by_zero"}.
All successful intermediates fit signed 32-bit integers. Tests do not combine
syntax errors with division-by-zero ambiguity.

### merge
Input: {"op":"merge","intervals":[[4,6],[1,3],[3,4]]}.
Sort closed ranges and merge overlaps or equal endpoints, producing
{"intervals":[[1,6]]}. Separated ranges such as [1,2] and [3,4] stay separate.
Any range with start greater than end returns {"error":"invalid_interval"}.
Empty input returns {"intervals":[]}. Integers fit signed 32-bit.

Unknown op returns {"error":"unknown_op"}. JSON formatting/key order is irrelevant.

