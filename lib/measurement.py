#!/usr/bin/env python3
"""Measure prebuilt file workers; correctness is checked against frozen JSONL.

Usage: python3 measure.py LANGUAGE STAGE validate|perf
       python3 measure.py all STAGE perf
No model calls, compilation, or business-logic implementation occurs here.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import random
import re
import signal
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parent
TIMEOUT_SECONDS = 30.0
TERMINATE_GRACE_SECONDS = 0.5
THREAD_ENV = {
    "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1", "BLIS_NUM_THREADS": "1",
}


def strict_equal(a, b):
    """Numeric 1 and 1.0 compare equally; bool must never equal a number."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return (not isinstance(a, float) or math.isfinite(a)) and (
            not isinstance(b, float) or math.isfinite(b)) and a == b
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(strict_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(strict_equal(x, y) for x, y in zip(a, b))
    return a == b


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _bad_constant(value):
    raise ValueError(f"nonstandard JSON numeric constant: {value}")


def parse_json(text):
    value = json.loads(text, object_pairs_hook=_object, parse_constant=_bad_constant)
    def finite(v):
        if isinstance(v, float) and not math.isfinite(v):
            raise ValueError("nonfinite JSON number")
        if isinstance(v, list):
            for x in v:
                finite(x)
        if isinstance(v, dict):
            for x in v.values():
                finite(x)
    finite(value)
    return value


def _lines(handle):
    for line_number, line in enumerate(handle, 1):
        if line.strip():
            yield line_number, line


def compare_output(actual_path, expected_path, expected_requests=None):
    result = {"correct": False, "actual_responses": 0,
              "expected_responses": 0, "mismatches": []}
    if not expected_path.is_file():
        result["checker_error"] = f"expected file missing: {expected_path}"
        return result
    if not actual_path.is_file():
        result["mismatches"].append({"error": "output file missing"})
        return result
    mismatch_count = 0
    sentinel = object()
    try:
        with actual_path.open(encoding="utf-8") as actual, expected_path.open(encoding="utf-8") as expected:
            for ordinal, (a, e) in enumerate(itertools.zip_longest(
                    _lines(actual), _lines(expected), fillvalue=sentinel), 1):
                if a is not sentinel:
                    result["actual_responses"] += 1
                if e is not sentinel:
                    result["expected_responses"] += 1
                error = None
                av = ev = None
                if a is sentinel:
                    error = "missing response"
                elif e is sentinel:
                    error = "extra response"
                else:
                    try:
                        ev = parse_json(e[1])
                    except (ValueError, RecursionError) as ex:
                        result["checker_error"] = f"invalid expected JSON at line {e[0]}: {ex}"
                        return result
                    try:
                        av = parse_json(a[1])
                    except (ValueError, RecursionError) as ex:
                        error = f"invalid response JSON at line {a[0]}: {ex}"
                    if error is None and not strict_equal(av, ev):
                        error = "response differs"
                if error:
                    mismatch_count += 1
                    if len(result["mismatches"]) < 3:
                        detail = {"response": ordinal, "error": error}
                        if a is not sentinel:
                            detail["actual_excerpt"] = a[1][:800].rstrip()
                        if e is not sentinel:
                            detail["expected_excerpt"] = e[1][:800].rstrip()
                        result["mismatches"].append(detail)
        if expected_requests is not None and result["expected_responses"] != expected_requests:
            result["checker_error"] = "expected-file response count differs from dataset metadata"
        result["mismatch_count"] = mismatch_count
        result["correct"] = mismatch_count == 0 and "checker_error" not in result
    except (OSError, UnicodeError, RecursionError) as ex:
        result["checker_error"] = f"unable to compare JSONL: {ex}"
    return result


def resolve_dataset_path(value, index_path):
    path = Path(value)
    if path.is_absolute():
        return path
    candidates = [ROOT / path, ROOT.parent / path, index_path.parent / path]
    return next((p.resolve() for p in candidates if p.exists()), candidates[0].resolve())


def process_group_members(group):
    """Best-effort observation only; rapid fork/exit is not fully observable."""
    try:
        probe = subprocess.run(["/bin/ps", "-axo", "pid=,pgid="],
                               capture_output=True, text=True, timeout=1)
        return [int(fields[0]) for line in probe.stdout.splitlines()
                if len(fields := line.split()) == 2 and int(fields[1]) == group]
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def warm_file(path):
    with path.open("rb") as source:
        while source.read(1024 * 1024):
            pass


def run_worker(worker, source, output, stdout_path, stderr_path):
    environment = os.environ.copy()
    environment.update(THREAD_ENV)
    done = threading.Event()
    observed = set()
    state = {"timed_out": False, "termination_signals": [], "tree_observation_errors": 0}
    result = {"command": [str(worker), str(source), str(output)],
              "timeout_seconds": TIMEOUT_SECONDS,
              "stdout_file": str(stdout_path), "stderr_file": str(stderr_path),
              "output_file": str(output), "runtime_environment": THREAD_ENV.copy(),
              "resource_scope": "wait4 child lifetime; reaped descendants as accounted by OS; RSS is not aggregate tree RSS"}
    start = time.perf_counter_ns()
    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            child = subprocess.Popen(result["command"], cwd=worker.parent,
                                     stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                     env=environment, start_new_session=True)
            def signal_group(sig):
                try:
                    os.killpg(child.pid, sig)
                    state["termination_signals"].append(signal.Signals(sig).name)
                except ProcessLookupError:
                    pass
            def watch():
                next_snapshot = time.monotonic() + 0.025
                deadline = time.monotonic() + TIMEOUT_SECONDS
                while not done.wait(0.01):
                    now = time.monotonic()
                    if now >= deadline:
                        state["timed_out"] = True
                        signal_group(signal.SIGTERM)
                        if not done.wait(TERMINATE_GRACE_SECONDS):
                            signal_group(signal.SIGKILL)
                        return
                    if now >= next_snapshot:
                        members = process_group_members(child.pid)
                        if members is None:
                            state["tree_observation_errors"] += 1
                        else:
                            observed.update(pid for pid in members if pid != child.pid)
                        next_snapshot = now + 0.5
            watcher = threading.Thread(target=watch, daemon=True)
            watcher.start()
            try:
                while True:
                    try:
                        _, status, usage = os.wait4(child.pid, 0)
                        break
                    except InterruptedError:
                        continue
                end = time.perf_counter_ns()
                child.returncode = os.waitstatus_to_exitcode(status)
            finally:
                done.set()
                watcher.join(timeout=1.2)
            result.update(elapsed_seconds=(end - start) / 1e9,
                          exit_code=child.returncode,
                          user_cpu_seconds=usage.ru_utime,
                          system_cpu_seconds=usage.ru_stime,
                          cpu_seconds=usage.ru_utime + usage.ru_stime,
                          peak_rss_raw=usage.ru_maxrss,
                          peak_rss_source_units="bytes" if sys.platform == "darwin" else "KiB" if sys.platform.startswith("linux") else "platform-dependent")
            if sys.platform == "darwin":
                result["peak_rss_bytes"] = usage.ru_maxrss
            elif sys.platform.startswith("linux"):
                result["peak_rss_bytes"] = usage.ru_maxrss * 1024
            if "peak_rss_bytes" in result:
                result["peak_rss_mib"] = result["peak_rss_bytes"] / 1048576
            # A still-live descendant makes process lifetime accounting incomplete.
            remaining = process_group_members(child.pid)
            result["remaining_process_group_members"] = remaining
            if remaining:
                result["process_tree_unsupported"] = True
                for sig in (signal.SIGTERM, signal.SIGKILL):
                    signal_group(sig)
                    time.sleep(0.02)
            result["observed_descendant_pids"] = sorted(observed)
            result["process_tree_observation"] = "best-effort snapshots; short-lived descendants may be missed; wrapper requires independent exec audit"
            result["process_tree_unsupported"] = result.get("process_tree_unsupported", False) or bool(observed)
            result["resource_accounting_supported"] = not result["process_tree_unsupported"]
            if result["process_tree_unsupported"]:
                result["resource_warning"] = "multiple application-group processes observed; direct-worker peak RSS is not summed tree memory; do not rank resource efficiency without audit"
    except OSError as ex:
        result.update(launch_error=str(ex), elapsed_seconds=(time.perf_counter_ns() - start) / 1e9)
    result.update(state)
    return result


def write_report(path, report):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    os.replace(temporary, path)


LANGUAGES = ("typescript", "python", "moonbit", "baml", "zero", "go", "rust", "swift", "kotlin")


def dataset_schedule(datasets, languages, mode, stage):
    """A recorded seed randomizes all (language,dataset) pairs in every block."""
    if mode == "validate":
        selected = [d for d in datasets if d.get("kind") == "validation"]
        return [(language, d, 0) for language in languages for d in selected], None
    selected = [d for d in datasets if (
        d.get("kind") in ("invoice", "access_log", "telemetry") and
        d.get("size") in ("medium", "large")) or d.get("kind") == "empty"]
    seed = int.from_bytes(hashlib.sha256(("deep-phase-perf:" + stage).encode()).digest()[:8], "big")
    rng = random.Random(seed)
    schedule = []
    for repetition in range(5):
        block = [(language, d, repetition) for language in languages for d in selected
                 if d.get("kind") != "empty" or repetition < 3]
        rng.shuffle(block)
        schedule.extend(block)
    return schedule, seed


def perform_case(context, dataset, repetition, global_sequence, stage, mode, index_path):
    sequence = len(context["report"]["records"])
    name = str(dataset.get("name", f"dataset_{sequence}"))
    record = {"language": context["language"], "dataset": name,
              "kind": dataset.get("kind"), "size": dataset.get("size"),
              "repetition": repetition, "sequence": sequence,
              "global_sequence": global_sequence,
              "items": dataset.get("items"), "requests": dataset.get("requests")}
    dataset_key = (name, str(dataset.get("input")))
    if mode == "perf" and context["validation_timeouts"] >= 2:
        record.update(skipped=True, valid=False, measured=False,
                      correctness_established=False,
                      reason="two prior timeouts: resource-budget stop; unmeasured not proven failure")
        return record
    if (mode == "perf" and dataset_key in context["failures"]) or (
            mode == "validate" and context["validation_timeouts"] >= 2):
        record.update(skipped=True, valid=False, measured=False,
                      correctness_established=False,
                      reason="prior dataset failure" if mode == "perf" else
                      "two prior validation timeouts; repeated-hang safeguard")
        return record
    try:
        source = resolve_dataset_path(dataset["input"], index_path)
        expected_field = "expected_maintenance" if stage == "maintenance" and dataset.get("expected_maintenance") else "expected"
        expected = resolve_dataset_path(dataset[expected_field], index_path)
        record.update(input=str(source), expected=str(expected))
        safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", name)[:80]
        stem = context["artifact_dir"] / f"{sequence:03d}_{safe_name}_r{repetition}"
        output = Path(str(stem) + ".output.jsonl")
        stdout = Path(str(stem) + ".stdout.log")
        stderr = Path(str(stem) + ".stderr.log")
        output.unlink(missing_ok=True)
        record["input_bytes"] = source.stat().st_size
        record["expected_bytes"] = expected.stat().st_size
        warm_file(source)
        record.update(run_worker(context["worker"], source, output, stdout, stderr))
        record["output_bytes"] = output.stat().st_size if output.exists() else 0
        record["stdout_bytes"] = stdout.stat().st_size if stdout.exists() else 0
        record["stderr_bytes"] = stderr.stat().st_size if stderr.exists() else 0
        comparison = compare_output(output, expected, dataset.get("requests"))
        record.update(comparison)
        record["valid"] = record.get("exit_code") == 0 and not record.get("timed_out") and comparison["correct"] and not record.get("remaining_process_group_members")
        if record["valid"] and record.get("resource_accounting_supported") and dataset.get("items", 0) > 0:
            record["cpu_seconds_per_million_input_items"] = record["cpu_seconds"] * 1_000_000 / dataset["items"]
        if record["valid"] and record.get("elapsed_seconds", 0) > 0:
            record["input_items_per_second"] = dataset.get("items", 0) / record["elapsed_seconds"]
        if record.get("timed_out"):
            context["validation_timeouts"] += 1
    except (OSError, ValueError, KeyError, TypeError) as ex:
        record.update(valid=False, measurement_error=f"{type(ex).__name__}: {ex}")
    if not record.get("valid"):
        context["failures"].add(dataset_key)
    return record


def summarize(report, planned):
    attempted = [r for r in report["records"] if not r.get("skipped")]
    report["summary"] = {"planned": planned, "attempted": len(attempted),
                         "valid": sum(bool(r.get("valid")) for r in attempted),
                         "skipped": sum(bool(r.get("skipped")) for r in report["records"]),
                         "pending": planned - len(report["records"]),
                         "all_valid": bool(attempted) and all(r.get("valid") for r in attempted) and len(attempted) == planned}


def measure(language, stage, mode):
    for value in (language, stage):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError("language and stage must be simple names")
    if language == "all" and mode != "perf":
        raise ValueError("all is supported for perf only; validate individual languages")
    languages = list(LANGUAGES) if language == "all" else [language]
    results_dir = ROOT / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    index_path = ROOT / "datasets" / "index.json"
    raw_index = json.loads(index_path.read_text())
    datasets = raw_index if isinstance(raw_index, list) else raw_index.get("datasets", raw_index.get("entries"))
    if not isinstance(datasets, list):
        raise ValueError("dataset index must be a list or contain datasets/entries list")
    datasets = [d for d in datasets if not d.get("stages") or stage in d["stages"]]
    schedule, seed = dataset_schedule(datasets, languages, mode, stage)
    contexts = {}
    for current in languages:
        artifact_dir = results_dir / f"{current}_{stage}_{mode}_artifacts"
        artifact_dir.mkdir(exist_ok=True)
        worker = ROOT / "runs" / current / "worker.sh"
        planned = sum(lang == current for lang, _, _ in schedule)
        report = {"language": current, "stage": stage, "mode": mode,
                  "worker": str(worker), "platform": sys.platform,
                  "measurement": "single prebuilt file worker; lifecycle CPU/RSS; warm filesystem cache; no per-record subprocess; correctness from independent expected JSONL",
                  "seed": seed,
                  "randomization_scope": "all nine language/dataset pairs within each repetition block" if language == "all" else "one language, dataset order within each repetition block",
                  "scheduled_languages": languages,
                  "expected_repetitions": 5 if mode == "perf" else 1,
                  "empty_repetitions": 3 if mode == "perf" else None,
                  "records": [], "limitations": [
                      "CPU/RSS include startup and worker shutdown, exclude builds and output checking.",
                      "Batch elapsed time does not provide individual-request p95/p99 or energy.",
                      "Process-tree checks are observational and require independent wrapper audit.",
                      "After two runtime timeouts per language/stage, remaining perf cases are unmeasured resource-budget skips, not proven failures."]}
        contexts[current] = {"language": current, "worker": worker, "report": report,
                             "path": results_dir / f"{current}_{stage}_{mode}.json",
                             "artifact_dir": artifact_dir, "failures": set(),
                             "validation_timeouts": 0, "planned": planned}
        summarize(report, planned)
        write_report(contexts[current]["path"], report)
    for global_sequence, (current, dataset, repetition) in enumerate(schedule):
        context = contexts[current]
        record = perform_case(context, dataset, repetition, global_sequence, stage, mode, index_path)
        context["report"]["records"].append(record)
        summarize(context["report"], context["planned"])
        write_report(context["path"], context["report"])
        print(json.dumps({k: record.get(k) for k in (
            "language", "dataset", "repetition", "global_sequence", "valid", "skipped",
            "elapsed_seconds", "cpu_seconds", "peak_rss_mib", "timed_out")}), flush=True)
    for context in contexts.values():
        print(json.dumps({"language": context["language"], "report": str(context["path"]),
                          **context["report"]["summary"]}), flush=True)
    return 0 if contexts and all(c["report"]["summary"]["all_valid"] for c in contexts.values()) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("language")
    parser.add_argument("stage")
    parser.add_argument("mode", choices=["validate", "perf"])
    args = parser.parse_args()
    # Serialize all invocations so competing measurements cannot overlap.
    (ROOT / "results").mkdir(exist_ok=True)
    with (ROOT / "results" / ".measure.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            return measure(args.language, args.stage, args.mode)
        except (OSError, ValueError, KeyError, TypeError) as ex:
            print(f"measurement setup error: {ex}", file=sys.stderr)
            return 2


if __name__ == "__main__":
    raise SystemExit(main())
