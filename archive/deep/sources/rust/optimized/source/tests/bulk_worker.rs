use serde_json::{Value, json};
use std::{fs, process::Command};

#[test]
fn prebuilt_worker_from_another_directory_processes_hundreds_of_lines() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    let dir = root.join(format!("test_artifacts_{}", std::process::id()));
    fs::create_dir_all(&dir).unwrap();
    let input = dir.join("input.jsonl");
    let output = dir.join("output.jsonl");
    let mut data = Vec::new();
    let mut expected = Vec::new();
    for i in 0..600 {
        if i % 4 == 0 {
            data.extend_from_slice(b"{bad\r\n");
            expected.push(json!({"error":"invalid_json"}));
        } else {
            let request = json!({"op":"telemetry","samples":[i,-i,5],"window":2,"threshold":0});
            serde_json::to_writer(&mut data, &request).unwrap();
            if i != 599 { data.extend_from_slice(b"\r\n\t\n"); }
            let last = (5-i)/2;
            expected.push(json!({"count":2,"min":last.min(0),"max":last.max(0),
                "above":i64::from(last>0),"weighted_checksum":2*last}));
        }
    }
    fs::write(&input, data).unwrap();
    let status = Command::new(root.join("worker.sh")).arg(&input).arg(&output)
        .current_dir("/private/tmp").output().unwrap();
    assert!(status.status.success(), "{}", String::from_utf8_lossy(&status.stderr));
    assert!(status.stdout.is_empty());
    let results: Vec<Value> = fs::read_to_string(&output).unwrap().lines()
        .map(|s| serde_json::from_str(s).unwrap()).collect();
    assert_eq!(results, expected);
    fs::remove_dir_all(dir).unwrap();
}
