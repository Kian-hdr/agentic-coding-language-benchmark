// Local deterministic specification and regression tests.
test "merge sorts and combines overlapping closed intervals" {
    assert.equal(merge([[4, 6], [1, 3], [3, 4]]), MergeReply { intervals: [[1, 6]] });
    assert.equal(merge([[1, 2], [3, 4]]), MergeReply { intervals: [[1, 2], [3, 4]] });
    assert.equal(
        merge([[5, 5], [1, 10], [1, 3], [1, 10], [10, 12]]),
        MergeReply { intervals: [[1, 12]] },
    );
    assert.equal(
        merge([[7, 8], [-4, -2], [-2, 0], [2, 2]]),
        MergeReply { intervals: [[-4, 0], [2, 2], [7, 8]] },
    );
    assert.equal(
        merge([[-2147483648, -2147483648], [2147483647, 2147483647]]),
        MergeReply { intervals: [[-2147483648, -2147483648], [2147483647, 2147483647]] },
    );
    assert.equal(
        merge([[2147483647, 2147483647], [-2147483648, 2147483647]]),
        MergeReply { intervals: [[-2147483648, 2147483647]] },
    )
}

test "merge empty input and invalid ranges" {
    assert.equal(merge([]), MergeReply { intervals: [] });
    assert.equal(merge([[2, 1]]), Failure { error: "invalid_interval" });
    assert.equal(merge([[1, 10], [5, 4]]), Failure { error: "invalid_interval" })
}

test "ledger normalizes groups and ignores later IDs" {
    assert.equal(
        ledger(
            [
                Entry { id: "a", account: " bank ", amount: 5 },
                Entry { id: "b", account: "bank", amount: -5 },
                Entry { id: "a", account: "", amount: 999 },
                Entry { id: "c", account: "\tZ\n", amount: 3 },
                Entry { id: "d", account: "A", amount: 2 },
            ],
        ),
        LedgerReply {
            accounts: [
                Account { account: "A", balance: 2, count: 1 },
                Account { account: "Z", balance: 3, count: 1 },
                Account { account: "bank", balance: 0, count: 2 },
            ],
            accepted: 4,
        },
    )
}

test "ledger empty and invalid accounts" {
    assert.equal(ledger([]), LedgerReply { accounts: [], accepted: 0 });
    assert.equal(
        ledger([Entry { id: "x", account: " \t\r\n\u000b\u000c", amount: 1 }]),
        Failure { error: "empty_account" },
    );
    assert.equal(trim_ascii(" \u00a0 "), "\u00a0");
    assert.equal(trim_ascii("a b"), "a b")
}

test "topo uses smallest currently available node and deduplicates" {
    assert.equal(
        topo(["z", "b", "a", "c"], [["a", "b"], ["a", "b"]]),
        TopoReply { order: ["a", "b", "c", "z"] },
    );
    assert.equal(
        topo(["b", "a", "c"], [["a", "b"], ["b", "c"]]),
        TopoReply { order: ["a", "b", "c"] },
    );
    assert.equal(topo(["b", "a", "c"], [["a", "c"]]), TopoReply { order: ["a", "b", "c"] });
    assert.equal(topo([], []), TopoReply { order: [] })
}

test "topo errors and unknown precedence" {
    assert.equal(topo(["a"], [["a", "a"]]), Failure { error: "cycle" });
    assert.equal(topo(["a", "b"], [["a", "b"], ["b", "a"]]), Failure { error: "cycle" });
    assert.equal(topo(["a"], [["a", "a"], ["b", "a"]]), Failure { error: "unknown_node" });
    assert.equal(topo([], [["x", "y"]]), Failure { error: "unknown_node" })
}

class CalculationCase {
    expr: string,
    value: int,
}

test "calculator arithmetic and precedence" {
    let cases = [
        CalculationCase { expr: "-(2 + 3) * 4 / 3", value: -6 },
        CalculationCase { expr: "2 + 3 * 4", value: 14 },
        CalculationCase { expr: "20/3/2", value: 3 },
        CalculationCase { expr: "10-3-2", value: 5 },
        CalculationCase { expr: "---+-5", value: 5 },
        CalculationCase { expr: "-7/3", value: -2 },
        CalculationCase { expr: "7/-3", value: -2 },
        CalculationCase { expr: "-7/-3", value: 2 },
        CalculationCase { expr: "1--2", value: 3 },
        CalculationCase { expr: "(1+(2*(3+4)))", value: 15 },
        CalculationCase { expr: "\t\r\n\u000b\u000c 00042 ", value: 42 },
        CalculationCase { expr: "0", value: 0 },
        CalculationCase { expr: "2147483647", value: 2147483647 },
        CalculationCase { expr: "-2147483648", value: -2147483648 },
    ];
    for (let c in cases) {
        assert.equal(calc(c.expr), CalcReply { value: c.value });
    }
}

test "calculator rejects malformed expressions" {
    let expressions = [
        "",
        " ",
        "()",
        "1+",
        "*2",
        "1 2",
        "2(3)",
        "(2)3",
        "(1",
        "1)",
        "1+()",
        "1.5",
        "1%2",
        "a",
        "1/**2",
        "+-",
        "\u00a01",
        "2**3",
        "((1)",
        "(1))",
        "1,2",
    ];
    for (let expr in expressions) {
        assert.equal(calc(expr), Failure { error: "syntax" });
    }
}

test "calculator division by zero" {
    for (let expr in ["1/0", "2/(1-1)", "1/-0", "0/0", "(1/0)"]) {
        assert.equal(calc(expr), Failure { error: "division_by_zero" });
    }
}
