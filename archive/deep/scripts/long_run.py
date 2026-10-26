#!/usr/bin/env python3
"""Final, startup-inclusive sustained-worker check. Run only after all stages.

Creates separate eight-block datasets; never rewrites frozen source datasets or
business implementations. Uses the existing resource/correctness machinery.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import time

import measure
from measure import compare_output, run_worker, warm_file
from oracle import solve

ROOT = Path(__file__).resolve().parent
KINDS = ("invoice", "access_log", "telemetry")
BLOCKS = 8
REPETITIONS = 2
TIMEOUT_SECONDS = 120.0
SEED = 2026102608


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    os.replace(temporary, path)


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def require_finished():
    for name in ("initial_complete", "optimized_complete", "all_complete"):
        marker = ROOT / "results" / name
        if not marker.is_file() or marker.read_text().strip() != "complete":
            raise ValueError(f"final-stage guard: missing completed marker {marker}")


def read_index(path):
    raw = json.loads(path.read_text())
    entries = raw if isinstance(raw, list) else raw.get("datasets", raw.get("entries")) if isinstance(raw, dict) else None
    if not isinstance(entries, list) or not all(isinstance(x, dict) for x in entries):
        raise ValueError("index must be a list or contain a datasets/entries list")
    selected = {}
    for kind in KINDS:
        matches = [x for x in entries if x.get("kind") == kind and x.get("size") == "large"
                   and (not x.get("stages") or "maintenance" in x["stages"])]
        if len(matches) != 1:
            raise ValueError(f"expected exactly one maintenance large dataset for {kind}")
        entry = matches[0]
        for key in ("items", "requests"):
            if type(entry.get(key)) is not int or entry[key] <= 0:
                raise ValueError(f"{kind}: invalid/missing positive integer metadata {key}")
        if not isinstance(entry.get("input"), str):
            raise ValueError(f"{kind}: missing input path")
        selected[kind] = entry
    return selected


def transform(request, kind, block):
    if not isinstance(request, dict) or request.get("op") != kind:
        raise ValueError(f"source request does not match dataset kind {kind}")
    if kind == "invoice":
        for event in request["events"]:
            event["id"] = f"block{block}:" + event["id"]
    elif kind == "access_log":
        shift = block * 100000
        request["start_ms"] += shift
        request["end_ms"] += shift
        for event in request["events"]:
            event["ts_ms"] += shift
    else:
        shift = block * 13
        request["samples"] = [value + shift for value in request["samples"]]
    return request


def generate(entry, kind, destination, index_path):
    source = measure.resolve_dataset_path(entry["input"], index_path)
    if not source.is_file():
        raise ValueError(f"source dataset missing: {source}")
    output = destination / f"{kind}_long.jsonl"
    expected = destination / f"{kind}_long.expected.jsonl"
    requests = items = 0
    with output.open("x", encoding="utf-8") as data, expected.open("x", encoding="utf-8") as answers:
        for block in range(BLOCKS):
            block_requests = block_items = 0
            with source.open(encoding="utf-8") as stream:
                for line in stream:
                    if not line.strip():
                        continue
                    request = transform(measure.parse_json(line), kind, block)
                    answer = solve(request, maintenance=True)
                    data.write(json.dumps(request, separators=(",", ":"), allow_nan=False) + "\n")
                    answers.write(json.dumps(answer, separators=(",", ":"), allow_nan=False) + "\n")
                    block_requests += 1
                    block_items += len(request["samples"] if kind == "telemetry" else request["events"])
            if block_requests != entry["requests"] or block_items != entry["items"]:
                raise ValueError(f"source metadata mismatch for {kind}: observed {block_requests} requests/{block_items} items")
            requests += block_requests
            items += block_items
    return {"name": f"{kind}_long", "kind": kind, "size": "long_8x_large",
            "source_dataset": entry.get("name", f"{kind}_large"),
            "source_input": str(source), "source_sha256": digest(source),
            "source_items": entry["items"], "source_requests": entry["requests"],
            "blocks": BLOCKS, "items": items, "requests": requests,
            "input": str(output), "expected": str(expected),
            "input_bytes": output.stat().st_size, "expected_bytes": expected.stat().st_size,
            "input_sha256": digest(output), "expected_sha256": digest(expected)}


def eligibility(language):
    worker = ROOT / "runs" / language / "worker.sh"
    build_path = ROOT / "results" / f"{language}_maintenance_build.json"
    validation_path = ROOT / "results" / f"{language}_maintenance_validate.json"
    reasons = []
    for path, label in ((build_path, "build"), (validation_path, "validation")):
        if not path.is_file():
            reasons.append(f"missing final maintenance {label} report")
    build = validation = None
    try:
        if build_path.is_file():
            build = json.loads(build_path.read_text())
            if build.get("exit_code") != 0:
                reasons.append("final maintenance build failed")
        if validation_path.is_file():
            validation = json.loads(validation_path.read_text())
            summary = validation.get("summary", {})
            records = validation.get("records", [])
            if (summary.get("all_valid") is not True or summary.get("pending") != 0
                    or not records or any(r.get("valid") is not True or r.get("skipped") for r in records)
                    or len(records) != summary.get("planned")):
                reasons.append("final maintenance validation not completely passing")
    except (ValueError, TypeError, AttributeError) as error:
        reasons.append(f"unreadable final evidence: {error}")
    if not worker.is_file() or not os.access(worker, os.X_OK):
        reasons.append("prebuilt worker launcher missing or not executable")
    return {"language": language, "eligible": not reasons, "reasons": reasons,
            "worker": str(worker), "build_report": str(build_path),
            "validation_report": str(validation_path),
            "build_report_sha256": digest(build_path) if build_path.is_file() else None,
            "validation_report_sha256": digest(validation_path) if validation_path.is_file() else None}


def summarize(report):
    records = report["records"]
    attempted = [r for r in records if r.get("measured")]
    report["summary"] = {"planned": len(report["schedule"]), "recorded": len(records),
                         "pending": len(report["schedule"]) - len(records),
                         "attempted": len(attempted),
                         "valid": sum(r.get("valid") is True for r in attempted),
                         "skipped": sum(r.get("skipped") is True for r in records),
                         "timeouts": sum(r.get("timed_out") is True for r in attempted)}


def execute():
    require_finished()
    measure.TIMEOUT_SECONDS = TIMEOUT_SECONDS
    index_path = ROOT / "datasets" / "index.json"
    entries = read_index(index_path)
    results = ROOT / "results"
    report_path = results / "long_run.json"
    dataset_dir = ROOT / "datasets" / "long_run"
    artifact_dir = results / "long_run_artifacts"
    # Refuse to overwrite an earlier or interrupted pass, including its failures.
    for path in (report_path, dataset_dir, artifact_dir):
        if path.exists():
            raise ValueError(f"preserving existing long-run artifacts; refusing overwrite: {path}")
    dataset_dir.mkdir()
    artifact_dir.mkdir()
    languages = [eligibility(language) for language in measure.LANGUAGES]
    schedule = []
    rng = random.Random(SEED)
    for repetition in range(REPETITIONS):
        block = [{"language": language["language"], "kind": kind, "repetition": repetition}
                 for language in languages for kind in KINDS]
        rng.shuffle(block)
        schedule.extend(block)
    report = {"stage": "maintenance_final_long_run", "status": "generating_datasets",
              "started_unix_seconds": time.time(), "timeout_seconds": TIMEOUT_SECONDS,
              "blocks": BLOCKS, "repetitions": REPETITIONS, "seed": SEED,
              "source_index": str(index_path), "source_index_sha256": digest(index_path),
              "eligibility": languages, "datasets": [], "schedule": schedule, "records": [],
              "limitations": [
                  "Single persistent prebuilt worker per run; no business-source edits or builds here.",
                  "Wall/CPU/RSS include startup, JVM JIT and shutdown; longer duration reduces but does not remove those effects.",
                  "Warm input-file cache; output comparison and oracle generation excluded from measured worker lifetime.",
                  "Peak RSS is direct-child lifetime maximum, not summed process-tree memory.",
                  "Batch results cannot establish HTTP behavior, request p99 latency, energy use or steady-state runtime throughput.",
                  "After two timeouts per language, remaining cases are unmeasured budget skips, not proven failures."]}
    summarize(report)
    save(report_path, report)
    try:
        for kind in KINDS:
            report["datasets"].append(generate(entries[kind], kind, dataset_dir, index_path))
            save(report_path, report)
        save(dataset_dir / "index.json", report["datasets"])
        report["status"] = "measuring"
        save(report_path, report)
        datasets = {d["kind"]: d for d in report["datasets"]}
        eligible = {entry["language"]: entry for entry in languages}
        timeouts = {language: 0 for language in measure.LANGUAGES}
        for sequence, case in enumerate(schedule):
            language, kind = case["language"], case["kind"]
            dataset = datasets[kind]
            record = {**case, "sequence": sequence, "dataset": dataset["name"],
                      "items": dataset["items"], "requests": dataset["requests"],
                      "blocks": BLOCKS, "input_bytes": dataset["input_bytes"],
                      "expected_bytes": dataset["expected_bytes"]}
            if not eligible[language]["eligible"] or timeouts[language] >= 2:
                record.update(skipped=True, measured=False, valid=False,
                              correctness_established=False,
                              reason="; ".join(eligible[language]["reasons"]) if not eligible[language]["eligible"] else
                              "two prior language timeouts; unmeasured resource-budget stop")
            else:
                stem = artifact_dir / f"{sequence:03d}_{language}_{kind}_r{case['repetition']}"
                output = Path(str(stem) + ".output.jsonl")
                stdout = Path(str(stem) + ".stdout.log")
                stderr = Path(str(stem) + ".stderr.log")
                record.update(measured=True, input=dataset["input"], expected=dataset["expected"])
                try:
                    warm_file(Path(dataset["input"]))
                    record.update(run_worker(Path(eligible[language]["worker"]), Path(dataset["input"]), output, stdout, stderr))
                    record["output_bytes"] = output.stat().st_size if output.is_file() else 0
                    record["output_sha256"] = digest(output) if output.is_file() else None
                    record["stdout_bytes"] = stdout.stat().st_size if stdout.is_file() else 0
                    record["stderr_bytes"] = stderr.stat().st_size if stderr.is_file() else 0
                    comparison = compare_output(output, Path(dataset["expected"]), dataset["requests"])
                    record.update(comparison)
                    record["valid"] = (record.get("exit_code") == 0 and not record.get("timed_out")
                                       and comparison["correct"] and not record.get("remaining_process_group_members"))
                    if record["valid"] and record.get("resource_accounting_supported"):
                        record["cpu_seconds_per_million_input_items"] = record["cpu_seconds"] * 1_000_000 / dataset["items"]
                    if record["valid"] and record.get("elapsed_seconds", 0) > 0:
                        record["input_items_per_second"] = dataset["items"] / record["elapsed_seconds"]
                    if record.get("timed_out"):
                        timeouts[language] += 1
                except (OSError, ValueError, KeyError, TypeError) as error:
                    record.update(valid=False, measurement_error=f"{type(error).__name__}: {error}")
            report["records"].append(record)
            summarize(report)
            save(report_path, report)
            # Only remove this invocation's verified-correct output; hashes/bytes
            # have already been durably recorded. All failure output/logs remain.
            if record.get("valid") and record.get("output_file"):
                created = Path(record["output_file"])
                if created.parent != artifact_dir or created != output:
                    raise ValueError("refusing cleanup outside exact task-created output")
                created.unlink()
                record["output_deleted_after_comparison"] = True
                save(report_path, report)
            print(json.dumps({key: record.get(key) for key in
                              ("language", "kind", "repetition", "valid", "skipped", "timed_out", "cpu_seconds", "elapsed_seconds", "peak_rss_mib")}), flush=True)
        report.update(status="complete", finished_unix_seconds=time.time())
        summarize(report)
        save(report_path, report)
        return 0
    except BaseException as error:
        report.update(status="interrupted" if isinstance(error, KeyboardInterrupt) else "infrastructure_error",
                      error=f"{type(error).__name__}: {error}")
        summarize(report)
        save(report_path, report)
        raise


def main():
    require_finished()
    with (ROOT / "results" / ".measure.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("another measurement owns .measure.lock; no long-run work started", file=sys.stderr)
            return 2
        require_finished()
        return execute()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"long-run setup/measurement error: {error}", file=sys.stderr)
        raise SystemExit(2)
