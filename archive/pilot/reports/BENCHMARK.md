# Agent language evaluation, 26 October 2026

Research and isolated evaluation only. Do not migrate an existing codebase.

## Frozen pilot design

Candidates: MoonBit, BAML, Zerolang. Baselines: strict TypeScript, Python,
Go, Rust, Swift, and Kotlin (user-expanded scope before those trials).
Model: GPT-6.1 Sol, medium reasoning, same Codex CLI and fixed instructions.
Two independent starts per available language, each with three initial tasks
and one later feature addition. Maximum 480 seconds per initial run and 240
seconds per extension; report timeouts and unavailable platforms explicitly.
These are pilot samples, not statistically conclusive rankings.

Each run supplies ./run.sh REQUEST_FILE. It reads a JSON request file and
prints exactly one JSON response. Shell/Python/Node wrappers may transport
input/output or launch the target executable, but all business logic must
be implemented in the assigned language. No third-party application packages.
Bundled standard libraries and compiler dependencies are allowed. Preregistered
JSON parsing libraries are additionally allowed for Rust (serde_json) and Kotlin
(org.json), because their standard libraries lack equivalent JSON support.
They are staged before the timer and implement no task business logic.

Agents receive identical specifications and public examples plus a short
language-specific documentation packet. They may inspect the installed
toolchain's documentation/standard library. No web, delegation, package
installation, or other-language implementations during timed trials.
They may compile, run, test and fix their code. Toolchain installation is
measured separately from authoring. Hidden evaluation is controlled by the
parent and never included in the agent's run folder.

## Initial tasks

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

Unknown op returns {"error":"unknown_op"}. JSON formatting/key order is irrelevant.

## Later change (not exposed during initial trials)

Add op merge. Input {"op":"merge","intervals":[[4,6],[1,3],[3,4]]}.
Treat intervals as closed ranges; sort and merge overlaps or equal endpoints,
but do not merge separated integer ranges such as [1,2] and [3,4].
Output {"intervals":[[1,6]]}. A range with start greater than end returns
{"error":"invalid_interval"}. Preserve all existing behavior.

## Measurements

Exact model identity/access, compiler versions, install obstacles, objective
correctness, regression rate, authoring wall time, input/output/cached tokens,
tool and repair calls, warm repeated workload timing, and qualitative usability.
Measure compiler/runtime speed separately from agent token efficiency.
No dollar-cost estimates without verified applicable model prices. Preserve
raw model events, generated source, prompts and evaluator outputs.

Support assessment separately covers governance, organization, release cadence,
license/forkability, ecosystem/interoperability and migration exit cost.
No probability of survival is asserted from these proxies.
