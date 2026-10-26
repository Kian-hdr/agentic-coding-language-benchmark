use serde_json::{Value, json};
use std::path::Path;
use std::process::Command;

#[test]
fn runner_reads_files_from_another_working_directory() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    for (fixture, expected) in [
        ("ledger", json!({"accounts":[{"account":"bank","balance":0,"count":2}],"accepted":2})),
        ("topo", json!({"order":["b","a","c","z"]})),
        ("calc", json!({"value":-6})),
        ("merge", json!({"intervals":[[1,6]]})),
    ] {
        let output = Command::new(root.join("run.sh"))
            .arg(root.join(format!("tests/fixtures/{fixture}.json")))
            .current_dir("/private/tmp")
            .output().expect("runner starts");
        assert!(output.status.success(), "{}", String::from_utf8_lossy(&output.stderr));
        let actual: Value = serde_json::from_slice(&output.stdout)
            .expect("stdout contains exactly one JSON response");
        assert_eq!(actual, expected);
    }
}
