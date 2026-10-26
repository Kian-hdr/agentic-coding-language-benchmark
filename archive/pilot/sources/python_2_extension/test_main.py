import json
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from main import respond


class OperationsTest(unittest.TestCase):
    def test_ledger_empty(self):
        self.assertEqual(respond({"op": "ledger", "entries": []}),
                         {"accounts": [], "accepted": 0})

    def test_ledger_normalization_duplicates_and_zero(self):
        self.assertEqual(respond({"op": "ledger", "entries": [
            {"id": "a", "account": " bank \t", "amount": 5},
            {"id": "a", "account": "", "amount": 100},
            {"id": "b", "account": "\r\nbank\v\f", "amount": -5},
            {"id": "c", "account": "Zoo", "amount": -2},
            {"id": "d", "account": "Alpha", "amount": 3},
        ]}), {"accounts": [
            {"account": "Alpha", "balance": 3, "count": 1},
            {"account": "Zoo", "balance": -2, "count": 1},
            {"account": "bank", "balance": 0, "count": 2},
        ], "accepted": 4})

    def test_ledger_empty_account(self):
        for account in ("", " \t\n\r\v\f"):
            self.assertEqual(respond({"op": "ledger", "entries": [
                {"id": "a", "account": account, "amount": 0}
            ]}), {"error": "empty_account"})

    def test_ledger_only_ascii_whitespace_trimmed(self):
        self.assertEqual(respond({"op": "ledger", "entries": [
            {"id": "a", "account": " \u00a0 ", "amount": 1}
        ]}), {"accounts": [{"account": "\u00a0", "balance": 1, "count": 1}],
              "accepted": 1})

    def test_topo_empty_and_disconnected(self):
        self.assertEqual(respond({"op": "topo", "nodes": [], "edges": []}),
                         {"order": []})
        self.assertEqual(respond({"op": "topo", "nodes": ["z", "a", "B"], "edges": []}),
                         {"order": ["B", "a", "z"]})

    def test_topo_dynamic_priority_and_duplicate_edges(self):
        self.assertEqual(respond({"op": "topo", "nodes": ["z", "a", "b"],
                                  "edges": [["b", "a"], ["b", "a"]]}),
                         {"order": ["b", "a", "z"]})

    def test_topo_cycles(self):
        for edges in ([["a", "a"]], [["a", "b"], ["b", "a"]]):
            self.assertEqual(respond({"op": "topo", "nodes": ["a", "b"], "edges": edges}),
                             {"error": "cycle"})

    def test_topo_unknown_precedes_cycle(self):
        for edge in (["x", "a"], ["a", "x"]):
            self.assertEqual(respond({"op": "topo", "nodes": ["a"],
                                      "edges": [["a", "a"], edge]}),
                             {"error": "unknown_node"})

    def test_calc_values(self):
        cases = {
            "-(2 + 3) * 4 / 3": -6,
            "2+3*4": 14, "(2+3)*4": 20,
            "20 / 3 / 2": 3, "10-3-2": 5,
            "-7/3": -2, "7/-3": -2, "-7/-3": 2,
            "1/-2": 0, "--+-5": -5,
            "2*-(-3+1)": 4, "1--2": 3,
            "0000012 + 03": 15, "\t\n\r\v\f 42 ": 42,
            "-2147483648": -2147483648,
            "2147483647": 2147483647,
            "1 + + + ( - - 2 ) * 3": 7,
        }
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertEqual(respond({"op": "calc", "expr": expression}),
                                 {"value": expected})

    def test_calc_syntax(self):
        cases = ["", " \t", "()", "(1", "1)", "1+", "*1", "1**2",
                 "1//2", "1 2", "2(3)", "(2)3", "(2)(3)", "1.0",
                 "0x10", "abc", "2^3", "1,2", "٢", "1\u00a0+2",
                 "(-)", "(1+)", "1+*2", ")1(", "1%2", "1=1"]
        for expression in cases:
            with self.subTest(expression=expression):
                self.assertEqual(respond({"op": "calc", "expr": expression}),
                                 {"error": "syntax"})

    def test_calc_division_by_zero(self):
        for expression in ("1/0", "2/(3-3)", "1 / -0", "0/0"):
            self.assertEqual(respond({"op": "calc", "expr": expression}),
                             {"error": "division_by_zero"})

    def test_calc_deep_input(self):
        for expression in ("(" * 5000 + "1" + ")" * 5000, "-" * 5000 + "1"):
            self.assertEqual(respond({"op": "calc", "expr": expression}), {"value": 1})

    def test_calc_generated_expressions(self):
        rng = random.Random(42)

        def generate(depth):
            if depth == 0 or rng.random() < 0.3:
                value = rng.randrange(10)
                return str(value), value
            if rng.random() < 0.25:
                expression, value = generate(depth - 1)
                return "-(" + expression + ")", -value
            left_expression, left = generate(depth - 1)
            right_expression, right = generate(depth - 1)
            operator = rng.choice("+-*/" if right else "+-*")
            if operator == "+":
                value = left + right
            elif operator == "-":
                value = left - right
            elif operator == "*":
                value = left * right
            else:
                # Small generated values permit an independent float-based oracle.
                value = int(left / right)
            return f"({left_expression} {operator} {right_expression})", value

        for _ in range(500):
            expression, expected = generate(4)
            self.assertEqual(respond({"op": "calc", "expr": expression}), {"value": expected})

    def test_unknown_operation(self):
        self.assertEqual(respond({"op": "other"}), {"error": "unknown_op"})

    def test_merge_ranges(self):
        cases = [
            ([], []),
            ([[4, 6], [1, 3], [3, 4]], [[1, 6]]),
            ([[3, 4], [1, 2]], [[1, 2], [3, 4]]),
            ([[1, 8], [2, 3], [1, 8], [8, 8]], [[1, 8]]),
            ([[5, 5], [-3, -1], [-1, 0], [2, 2]],
             [[-3, 0], [2, 2], [5, 5]]),
            ([[-2147483648, -2147483648], [2147483647, 2147483647]],
             [[-2147483648, -2147483648], [2147483647, 2147483647]]),
        ]
        for intervals, expected in cases:
            with self.subTest(intervals=intervals):
                original = [interval[:] for interval in intervals]
                self.assertEqual(respond({"op": "merge", "intervals": intervals}),
                                 {"intervals": expected})
                self.assertEqual(intervals, original)

    def test_merge_invalid_interval(self):
        for intervals in ([[2, 1]], [[0, 10], [5, 4]],
                          [[2147483647, -2147483648], [1, 2]]):
            self.assertEqual(respond({"op": "merge", "intervals": intervals}),
                             {"error": "invalid_interval"})

    def test_launcher_json_protocol(self):
        root = Path(__file__).resolve().parent
        requests = [
            ({"op": "ledger", "entries": []}, {"accounts": [], "accepted": 0}),
            ({"op": "topo", "nodes": ["a", "b"], "edges": [["a", "b"]]},
             {"order": ["a", "b"]}),
            ({"op": "calc", "expr": "-(2+3)*4/3"}, {"value": -6}),
            ({"op": "calc", "expr": "1/0"}, {"error": "division_by_zero"}),
            ({"op": "merge", "intervals": [[4, 6], [1, 3], [3, 4]]},
             {"intervals": [[1, 6]]}),
            ({"op": "merge", "intervals": []}, {"intervals": []}),
            ({"op": "merge", "intervals": [[2, 1]]},
             {"error": "invalid_interval"}),
            ({"op": "unknown"}, {"error": "unknown_op"}),
        ]
        with tempfile.TemporaryDirectory(prefix="Test_", dir=root) as directory:
            request_file = Path(directory) / "Request_File.json"
            for request, expected in requests:
                request_file.write_text(json.dumps(request), encoding="utf-8")
                result = subprocess.run([str(root / "run.sh"), str(request_file)],
                                        capture_output=True, text=True, check=True, cwd=directory)
                self.assertEqual(result.stderr, "")
                self.assertEqual(len(result.stdout.splitlines()), 1)
                self.assertEqual(json.loads(result.stdout), expected)


if __name__ == "__main__":
    unittest.main()
