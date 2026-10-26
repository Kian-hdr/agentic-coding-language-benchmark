// Offline regression tests for all specified behavior.
function expect(raw: string, expected: Reply) -> void {
    assert.equal(dispatch(raw), expected);
}

test "ledger empty and grouping" {
    expect(`{"op":"ledger","entries":[]}`, LedgerReply { accounts: [], accepted: 0 });
    expect(
        `{"op":"ledger","entries":[{"id":"a","account":" bank ","amount":5},{"id":"b","account":"bank","amount":-5},{"id":"c","account":"A","amount":7},{"id":"a","account":"","amount":99}]}`,
        LedgerReply {
            accounts: [
                Account { account: "A", balance: 7, count: 1 },
                Account { account: "bank", balance: 0, count: 2 },
            ],
            accepted: 3,
        },
    );
    expect(
        `{"op":"ledger","entries":[{"id":"a","account":"","amount":0}]}`,
        ErrorReply { error: "empty_account" },
    );
    expect(
        `{"op":"ledger","entries":[{"id":"a","account":"x","amount":1},{"id":"b","account":"  ","amount":2}]}`,
        ErrorReply { error: "empty_account" },
    )
}

test "ASCII whitespace precisely" {
    let spaces = string.from_code_points([9, 10, 11, 12, 13, 32]);
    assert.equal(trim_ascii(spaces + "bank" + spaces), "bank");
    assert.equal(
        ledger([Entry { id: "1", account: spaces, amount: 0 }]),
        ErrorReply { error: "empty_account" },
    );
    let nonascii = string.from_code_points([160]);
    assert.equal(trim_ascii(nonascii + "x" + nonascii), nonascii + "x" + nonascii);
    assert.equal(calc("1" + spaces + "+ 2"), CalcReply { value: 3 });
    assert.equal(calc("1" + nonascii + "+2"), ErrorReply { error: "syntax" })
}

test "topo lexicographic priority and duplicates" {
    expect(`{"op":"topo","nodes":[],"edges":[]}`, TopoReply { order: [] });
    expect(
        `{"op":"topo","nodes":["z","b","a","A"],"edges":[]}`,
        TopoReply { order: ["A", "a", "b", "z"] },
    );
    expect(
        `{"op":"topo","nodes":["z","b","a"],"edges":[["b","a"],["b","a"]]}`,
        TopoReply { order: ["b", "a", "z"] },
    );
    expect(
        `{"op":"topo","nodes":["d","c","b","a"],"edges":[["a","c"],["b","c"],["c","d"]]}`,
        TopoReply { order: ["a", "b", "c", "d"] },
    )
}

test "topo errors and unknown priority" {
    expect(`{"op":"topo","nodes":["a"],"edges":[["a","a"]]}`, ErrorReply { error: "cycle" });
    expect(
        `{"op":"topo","nodes":["a","b","c"],"edges":[["a","b"],["b","a"]]}`,
        ErrorReply { error: "cycle" },
    );
    expect(
        `{"op":"topo","nodes":["a"],"edges":[["a","a"],["a","x"]]}`,
        ErrorReply { error: "unknown_node" },
    );
    expect(`{"op":"topo","nodes":["a"],"edges":[["x","a"]]}`, ErrorReply { error: "unknown_node" });
    expect(`{"op":"topo","nodes":[],"edges":[["x","x"]]}`, ErrorReply { error: "unknown_node" })
}

class CalcCase {
    expr: string,
    value: int,
}

test "calculator values" {
    let cases = [
        CalcCase { expr: "-(2 + 3) * 4 / 3", value: -6 },
        CalcCase { expr: "2 + 3 * 4", value: 14 },
        CalcCase { expr: "20/3/2", value: 3 },
        CalcCase { expr: "10-3-2", value: 5 },
        CalcCase { expr: "--+-+5", value: -5 },
        CalcCase { expr: "2*-(-3)", value: 6 },
        CalcCase { expr: "7/-3", value: -2 },
        CalcCase { expr: "-7/3", value: -2 },
        CalcCase { expr: "-7/-3", value: 2 },
        CalcCase { expr: "2--3", value: 5 },
        CalcCase { expr: "000012", value: 12 },
        CalcCase { expr: "((1))", value: 1 },
        CalcCase { expr: "0", value: 0 },
        CalcCase { expr: "2147483647", value: 2147483647 },
        CalcCase { expr: "-2147483648", value: -2147483648 },
    ];
    for (let c in cases) {
        assert.equal(calc(c.expr), CalcReply { value: c.value });
    }
}

test "calculator syntax and zero division" {
    let invalid = [
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
        "1.2",
        "a",
        "2**3",
        "2//3",
        "+",
        "1 + ()",
        "(1+2))",
        "((1)",
        "1,2",
        "1e2",
        "0x10",
        "１",
        "1=2",
        "1/*2",
    ];
    for (let expr in invalid) {
        assert.equal(calc(expr), ErrorReply { error: "syntax" });
    }
    for (let expr in ["1/0", "2/(3-3)", "0/0", "3/-0"]) {
        assert.equal(calc(expr), ErrorReply { error: "division_by_zero" });
    }
}

test "calculator generated arithmetic" {
    let a = -12;
    while (a <= 12) {
        let b = -6;
        while (b <= 6) {
            assert.equal(calc(`(${a})+(${b})*3`), CalcReply { value: a + b * 3 });
            assert.equal(calc(`(${a})-(${b})-2`), CalcReply { value: a - b - 2 });
            if (b != 0) {
                assert.equal(calc(`(${a})/(${b})`), CalcReply { value: a / b });
            }
            b += 1;
        }
        a += 1;
    }
}

test "unknown operation" {
    expect(`{"op":"other"}`, ErrorReply { error: "unknown_op" })
}
