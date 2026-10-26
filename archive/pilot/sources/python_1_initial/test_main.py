import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from main import calc, ledger, respond, topo


class OperationTests(unittest.TestCase):
    def test_ledger_empty(self):
        self.assertEqual(ledger([]), {"accounts": [], "accepted": 0})

    def test_ledger_normalization_duplicates_and_zero(self):
        self.assertEqual(ledger([
            {"id": "1", "account": " bank\t", "amount": 5},
            {"id": "1", "account": "", "amount": 999},
            {"id": "2", "account": "bank", "amount": -5},
            {"id": "3", "account": " A\r\n\v\f", "amount": -2},
        ]), {"accounts": [
            {"account": "A", "balance": -2, "count": 1},
            {"account": "bank", "balance": 0, "count": 2},
        ], "accepted": 3})

    def test_ledger_empty_account(self):
        self.assertEqual(ledger([{"id": "a", "account": " \t\r\n\v\f", "amount": 0}]),
                         {"error": "empty_account"})

    def test_ledger_only_ascii_whitespace_trimmed(self):
        self.assertEqual(ledger([{"id": "a", "account": "\u00a0", "amount": 1}]),
                         {"accounts": [{"account": "\u00a0", "balance": 1, "count": 1}],
                          "accepted": 1})

    def test_topo(self):
        cases = [
            ([], [], {"order": []}),
            (["b", "a"], [], {"order": ["a", "b"]}),
            (["a", "b", "c"], [["a", "b"], ["a", "b"]], {"order": ["a", "b", "c"]}),
            (["a", "b", "c", "z"], [["a", "b"], ["b", "c"]],
             {"order": ["a", "b", "c", "z"]}),
            (["a"], [["a", "a"]], {"error": "cycle"}),
            (["a", "b"], [["a", "b"], ["b", "a"]], {"error": "cycle"}),
            (["a"], [["a", "a"], ["a", "x"]], {"error": "unknown_node"}),
            ([], [["x", "y"]], {"error": "unknown_node"}),
        ]
        for nodes, edges, expected in cases:
            with self.subTest(nodes=nodes, edges=edges):
                self.assertEqual(topo(nodes, edges), expected)

    def test_calc_values(self):
        cases = {
            "-(2 + 3) * 4 / 3": -6, "1+2*3": 7, "8/3*3": 6,
            "8-3-2": 3, "-7/3": -2, "7/-3": -2, "-7/-3": 2,
            "--+-2": -2, "1--2": 3, "2*-(-3+1)": 4,
            "00012": 12, " \t\n\r\v\f +0 ": 0, "1/-2": 0,
            "2147483647": 2147483647, "-2147483648": -2147483648,
            "2/--2": 1, "-(+(-(+2)))": 2,
        }
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertEqual(calc(expression), {"value": expected})

    def test_calc_syntax(self):
        for expression in ["", " ", "()", "1+", "*1", "1 2", "2(3)", "(2)3",
                           "(1", "1)", "1.0", "1a", "2**3", "2//3", "-", "(+)",
                           "1\u00a0+2", "١", "(1)(2)", "1,2", "1+*2"]:
            with self.subTest(expression=expression):
                self.assertEqual(calc(expression), {"error": "syntax"})

    def test_calc_zero_division(self):
        for expression in ["1/0", "1/(2-2)", "0/0", "3/-0"]:
            with self.subTest(expression=expression):
                self.assertEqual(calc(expression), {"error": "division_by_zero"})

    def test_calc_deep_nesting_and_unary(self):
        self.assertEqual(calc("(" * 5000 + "1" + ")" * 5000), {"value": 1})
        self.assertEqual(calc("-" * 5001 + "1"), {"value": -1})

    def test_unknown(self):
        self.assertEqual(respond({"op": "other"}), {"error": "unknown_op"})

    def test_executable_protocol(self):
        root = Path(__file__).resolve().parent
        for request, expected in [
            ({"op": "calc", "expr": "-(2+3)*4/3"}, {"value": -6}),
            ({"op": "ledger", "entries": []}, {"accounts": [], "accepted": 0}),
            ({"op": "topo", "nodes": [], "edges": []}, {"order": []}),
            ({"op": "unknown"}, {"error": "unknown_op"}),
        ]:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", dir=root) as file:
                json.dump(request, file)
                file.flush()
                completed = subprocess.run([str(root / "run.sh"), file.name],
                                           capture_output=True, text=True, check=True, cwd=root)
                self.assertEqual(completed.stderr, "")
                self.assertEqual(len(completed.stdout.splitlines()), 1)
                self.assertEqual(json.loads(completed.stdout), expected)


if __name__ == "__main__":
    unittest.main()
