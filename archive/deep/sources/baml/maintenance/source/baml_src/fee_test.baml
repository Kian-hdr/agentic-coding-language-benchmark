test "optional invoice fees per paid event and isolation" {
    let events = `[{"id":"a","customer":" B ","amount_cents":5,"status":"paid"},{"id":"b","customer":"B","amount_cents":5,"status":"paid"},{"id":"c","customer":"B","amount_cents":5,"status":"refund"},{"id":"d","customer":"A","amount_cents":4,"status":"paid"},{"id":"d","customer":"A","amount_cents":500,"status":"paid"},{"id":"bad","customer":" ","amount_cents":50,"status":"paid"},{"id":"bad","customer":"A","amount_cents":50,"status":"paid"},{"id":"p","customer":"A","amount_cents":500,"status":"pending"},{"id":"v","customer":"A","amount_cents":500,"status":"void"},{"id":"n","customer":"A","amount_cents":-1,"status":"paid"},{"id":"s","customer":"A","amount_cents":50,"status":"unknown"}]`;
    let legacy = `{"op":"invoice","events":` + events + `}`;
    let before = process(legacy);
    assert.equal(
        decoded(`{"op":"invoice","fee_bps":1000,"events":` + events + `}`),
        baml.json.parse(
            `{"customers":[{"customer":"A","gross_cents":4,"refund_cents":0,"net_cents":4,"count":1,"fee_cents":0},{"customer":"B","gross_cents":10,"refund_cents":5,"net_cents":3,"count":3,"fee_cents":2}],"accepted":4,"duplicates":2,"ignored":2,"rejected":3,"gross_cents":14,"refund_cents":5,"net_cents":7,"fee_cents":2}`,
        ),
    );
    assert.equal(
        decoded(
            `{"op":"invoice","fee_bps":0,"events":[{"id":"a","customer":"A","amount_cents":9007199254740991,"status":"paid"}]}`,
        ),
        baml.json.parse(
            `{"customers":[{"customer":"A","gross_cents":9007199254740991,"refund_cents":0,"net_cents":9007199254740991,"count":1,"fee_cents":0}],"accepted":1,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":9007199254740991,"refund_cents":0,"net_cents":9007199254740991,"fee_cents":0}`,
        ),
    );
    assert.equal(
        decoded(
            `{"op":"invoice","fee_bps":1,"events":[{"id":"a","customer":"A","amount_cents":9007199254735991,"status":"paid"}]}`,
        ),
        baml.json.parse(
            `{"customers":[{"customer":"A","gross_cents":9007199254735991,"refund_cents":0,"net_cents":9006298534810517,"count":1,"fee_cents":900719925474}],"accepted":1,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":9007199254735991,"refund_cents":0,"net_cents":9006298534810517,"fee_cents":900719925474}`,
        ),
    );
    assert.equal(
        decoded(`{"op":"invoice","fee_bps":1000,"events":[]}`),
        baml.json.parse(
            `{"customers":[],"accepted":0,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":0,"refund_cents":0,"net_cents":0,"fee_cents":0}`,
        ),
    );
    assert.equal(
        decoded(
            `{"op":"invoice","fee_bps":1000,"events":[{"id":"r","customer":"R","amount_cents":100,"status":"refund"}]}`,
        ),
        baml.json.parse(
            `{"customers":[{"customer":"R","gross_cents":0,"refund_cents":100,"net_cents":-100,"count":1,"fee_cents":0}],"accepted":1,"duplicates":0,"ignored":0,"rejected":0,"gross_cents":0,"refund_cents":100,"net_cents":-100,"fee_cents":0}`,
        ),
    );
    assert.equal(process(legacy), before);
}
