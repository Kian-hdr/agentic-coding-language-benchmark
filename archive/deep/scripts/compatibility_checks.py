#!/usr/bin/env python3
"""Post-benchmark compatibility evidence, never a cross-device certification.

Run only after all model and performance stages:
  python3 compatibility_checks.py --after-stages-complete
No downloads, signing, installation, source edits or benchmark artifact replacement.
"""
from __future__ import annotations
import argparse
import ast
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
OUT = ROOT / 'compatibility'
LANGS = ['python', 'typescript', 'go', 'rust', 'swift', 'kotlin', 'moonbit', 'baml', 'zero']
GO = BASE / 'toolchains/go/go/bin/go'
SWIFTC = Path('{ORIGINAL_XCODE_APP}/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc')
NODE = Path('{ORIGINAL_HOMEBREW}/bin/node')
JAVA = Path('{ORIGINAL_HOMEBREW}/opt/openjdk@21/bin/java')
RECORDS = []


def save():
    report = {'scope': 'Post-stage local compatibility checks; no clean-device or remote-device execution',
              'host': {'system': os.uname().sysname, 'release': os.uname().release,
                       'machine': os.uname().machine},
              'limitations': ['Only this Mac is used for execution.',
                  'Linux/Windows cross-builds are not target-OS runtime tests.',
                  'Rosetta, if already available, is translation on the same Mac, not an Intel-device test.',
                  'No installers, signing, notarization, stores, updates, UI or mobile devices tested.',
                  'Python alternate versions run source, not foreign-version .pyc files.',
                  'Missing interpreters, SDKs and dependencies are recorded without installation.',
                  'Mach-O deployment minima describe binary metadata, not tests on those older OS versions.',
                  'Kotlin JVM JAR requires JRE21 and is not an Android APK; Android deployment is untested.'],
              'records': RECORDS}
    (OUT / 'results.json').write_text(json.dumps(report, indent=2) + '\n')


def skip(name, reason):
    RECORDS.append({'name': name, 'status': 'skipped', 'reason': reason,
                    'build': 'not_attempted', 'run': 'not_attempted',
                    'clean_device': 'untested'})
    save()


def command(name, argv, *, cwd=None, env=None, timeout=180, artifact=None, output_limit=12000):
    started = time.monotonic()
    rec = {'name': name, 'command': [str(x) for x in argv],
           'cwd': str(cwd or OUT), 'clean_device': 'untested'}
    if env:
        rec['environment_overrides'] = env
    try:
        p = subprocess.run([str(x) for x in argv], cwd=cwd or OUT,
                           env={**os.environ, **(env or {}), 'PYTHONDONTWRITEBYTECODE': '1'},
                           capture_output=True, text=True, errors='replace', timeout=timeout)
        rec.update(exit_code=p.returncode, stdout=p.stdout[-output_limit:], stderr=p.stderr[-output_limit:],
                   status='passed' if p.returncode == 0 else 'failed')
    except subprocess.TimeoutExpired as e:
        rec.update(exit_code=None, status='timeout', error=str(e))
    except OSError as e:
        rec.update(exit_code=None, status='unavailable', error=str(e))
    rec['seconds'] = time.monotonic() - started
    if artifact is not None and artifact.is_file():
        rec['artifact'] = str(artifact)
        rec['sha256'] = hashlib.sha256(artifact.read_bytes()).hexdigest()
        ft = subprocess.run(['/usr/bin/file', str(artifact)], capture_output=True, text=True)
        rec['file_type'] = ft.stdout.strip()
    RECORDS.append(rec)
    save()
    return rec


def tiny_dataset():
    """Select representative requests and frozen expectations without invoking oracle."""
    rows = []; wanted = {'invoice', 'access_log', 'telemetry', 'invalid_json', 'unknown_op'}
    for stem in ['validation', 'fee_validation']:
        source = ROOT / 'datasets' / (stem + '.jsonl')
        expected = ROOT / 'datasets' / (stem + '.maintenance.expected.jsonl')
        inputs = [x for x in source.read_text().splitlines() if x.strip()]
        outputs = [x for x in expected.read_text().splitlines() if x.strip()]
        if len(inputs) != len(outputs):
            raise ValueError('Frozen input/expectation count mismatch: ' + stem)
        for raw, result in zip(inputs, outputs):
            obj = json.loads(result)
            try:
                req = json.loads(raw); key = req.get('op', 'unknown_op')
                if key not in {'invoice', 'access_log', 'telemetry'}: key = 'unknown_op'
            except ValueError:
                key = 'invalid_json'
            if stem == 'fee_validation':
                rows.append((raw, result)); break
            if key in wanted:
                rows.append((raw, result)); wanted.remove(key)
    inp = OUT / 'tiny_input.jsonl'; exp = OUT / 'tiny_expected.jsonl'
    inp.write_text('\n'.join(r[0] for r in rows) + '\n')
    exp.write_text('\n'.join(r[1] for r in rows) + '\n')
    return inp, exp


def run_worker(name, argv, inp, expected, env=None):
    output = OUT / (name + '.output.jsonl')
    if output.exists():
        raise RuntimeError('Refusing stale output overwrite: ' + str(output))
    rec = command(name, [*argv, inp, output], env=env, timeout=60)
    rec['run'] = 'local_runtime_attempted'; rec['target_device'] = 'current_mac'
    if rec.get('exit_code') == 0:
        try:
            # Reuse the established strict JSON checker, not Python bool/int equality.
            import measure
            result = measure.compare_output(output, expected)
            rec['correctness'] = result
            if not result.get('correct'): rec['status'] = 'incorrect_output'
        except Exception as e:
            rec.update(status='checker_error', checker_error=str(e))
    save()
    return rec


def parse_macho_load_commands(raw):
    slices = []; current_arch = 'single_slice_or_unspecified'; active = None
    for line in raw.splitlines():
        arch = re.search(r'\(architecture ([^)]+)\)', line)
        if arch: current_arch = arch.group(1)
        text = line.strip()
        if text.startswith('Load command '): active = None
        if text in ['cmd LC_BUILD_VERSION', 'cmd LC_VERSION_MIN_MACOSX']:
            active = {'architecture': current_arch, 'load_command': text.split()[1]}
            slices.append(active)
        elif active is not None:
            fields = text.split()
            if len(fields) >= 2:
                # LC_BUILD_VERSION also contains nested linker/tool `version`.
                # Only its `minos` is deployment metadata; legacy LC_VERSION_MIN
                # uses `version` instead. Never mix these two command schemas.
                if active['load_command'] == 'LC_BUILD_VERSION':
                    allowed = {'platform': 'platform', 'minos': 'minimum_os', 'sdk': 'sdk'}
                else:
                    allowed = {'version': 'minimum_os', 'sdk': 'sdk'}
                if fields[0] in allowed:
                    active[allowed[fields[0]]] = fields[1]
    return slices


def macho_metadata(name, artifact):
    if not artifact.is_file():
        skip(name, 'Native artifact missing: ' + str(artifact)); return
    rec = command(name, ['/usr/bin/otool', '-l', artifact], artifact=artifact, output_limit=1000000)
    rec.update(evidence='native_artifact_load_commands', old_os_runtime='untested',
               language_platform_support='not_inferred_from_artifact', build='preexisting_or_separate_variant')
    raw = rec.get('stdout', '')
    (OUT / (name + '.otool.txt')).write_text(raw)
    slices = parse_macho_load_commands(raw)
    rec['deployment_load_commands'] = slices
    if rec.get('exit_code') == 0 and not slices:
        rec['metadata_limitation'] = 'No LC_BUILD_VERSION/LC_VERSION_MIN_MACOSX found; no minimum inferred'
    save()


def inspect_native_artifacts():
    paths = {
        'go': 'program', 'swift': 'program', 'zero': 'program', 'baml': 'worker',
        'rust': 'target/release/agent_benchmark',
        'moonbit': '_build/native/release/build/cmd/main/main.exe',
    }
    for lang, suffix in paths.items():
        macho_metadata(lang + '_original_macho_metadata', ROOT / 'runs' / lang / suffix)


def go_builds():
    source = ROOT / 'runs/go/main.go'
    if not GO.is_file() or not source.is_file():
        skip('go_cross_builds', 'Pinned Go compiler or final main.go unavailable'); return
    for system in ['linux', 'windows']:
        for arch in ['amd64', 'arm64']:
            name = 'go_' + system + '_' + arch
            folder = OUT / name; folder.mkdir()
            artifact = folder / ('worker.exe' if system == 'windows' else 'worker')
            rec = command(name, [GO, 'build', '-trimpath', '-ldflags=-s -w', '-o', artifact, source],
                          cwd=folder, env={'GOOS': system, 'GOARCH': arch, 'CGO_ENABLED': '0',
                          'GOTOOLCHAIN': 'local', 'GOCACHE': str(folder / 'cache'),
                          'GOMODCACHE': str(folder / 'modules'), 'GOPROXY': 'off', 'GOSUMDB': 'off'},
                          artifact=artifact)
            rec.update(build='cross_build_attempted', run='not_run_on_target_os',
                       target={'os': system, 'architecture': arch})
            save()


def swift_checks(inp, expected):
    source = ROOT / 'runs/swift/main.swift'; native = ROOT / 'runs/swift/program'
    if native.is_file():
        preserved = OUT / 'swift_native_original'; shutil.copy2(native, preserved)
        command('swift_native_file', ['/usr/bin/file', preserved], artifact=preserved)
        run_worker('swift_native_local', [preserved], inp, expected)
    if not source.is_file() or not SWIFTC.is_file():
        skip('swift_x86_build', 'Swift source or installed compiler unavailable'); return
    sdk = command('swift_sdk', ['/usr/bin/xcrun', '--sdk', 'macosx', '--show-sdk-path'])
    if sdk.get('exit_code') != 0:
        skip('swift_x86_build', 'Existing macOS SDK unavailable'); return
    built = {}
    for arch in ['x86_64', 'arm64']:
        artifact = OUT / ('swift_' + arch + '_macos13')
        rec = command('swift_' + arch + '_macos13_build', [SWIFTC, '-O',
                      '-whole-module-optimization', '-sdk', sdk['stdout'].strip(),
                      '-target', arch + '-apple-macosx13.0', '-module-cache-path',
                      OUT / ('swift_modules_' + arch), source, '-o', artifact], artifact=artifact)
        rec.update(build='separate_explicit_deployment_target_variant', run='build_only',
                   requested_minimum_os='macOS 13.0', target_architecture=arch,
                   old_os_runtime='untested', benchmark_artifact_replaced=False)
        save()
        if rec.get('exit_code') == 0:
            built[arch] = artifact
            macho_metadata('swift_' + arch + '_macos13_macho_metadata', artifact)
    if 'x86_64' in built:
        translated = command('rosetta_existing_probe', ['/usr/bin/arch', '-x86_64', '/usr/bin/true'])
        if translated.get('exit_code') == 0:
            rec = run_worker('swift_x86_translated_local', ['/usr/bin/arch', '-x86_64',
                             built['x86_64']], inp, expected)
            rec.update(execution_mode='existing_rosetta_translation', old_os_runtime='untested')
            save()
        else:
            skip('swift_x86_runtime', 'Existing Rosetta execution unavailable; no installation attempted')
    if len(built) == 2 and shutil.which('lipo'):
        universal = OUT / 'swift_universal_macos13'
        rec = command('swift_universal_macos13_build', ['lipo', '-create', built['arm64'],
                      built['x86_64'], '-output', universal], artifact=universal)
        rec.update(build='separate_explicit_deployment_target_variant', run='build_only',
                   old_os_runtime='untested', benchmark_artifact_replaced=False)
        save()
        if rec.get('exit_code') == 0:
            macho_metadata('swift_universal_macos13_macho_metadata', universal)


def python_checks(inp, expected):
    folder = ROOT / 'runs/python'
    source = next((folder / n for n in ['main.py', 'worker.py'] if (folder / n).is_file()), None)
    if source is None:
        skip('python_alternates', 'No source found; alternate versions cannot run foreign-version pyc'); return
    # Source inspection only. Missing imported packages are prerequisites, never auto-installed.
    imports = set()
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node, ast.Import): imports.update(x.name.split('.')[0] for x in node.names)
        if isinstance(node, ast.ImportFrom) and node.module: imports.add(node.module.split('.')[0])
    for version in ['3.12', '3.13']:
        interpreter = Path('{ORIGINAL_HOMEBREW}/bin/python' + version)
        name = 'python_' + version.replace('.', '_')
        if not interpreter.is_file(): skip(name, 'Requested existing interpreter unavailable'); continue
        command(name + '_version', [interpreter, '--version'])
        if 'numpy' in imports:
            dependency = command(name + '_numpy_prerequisite', [interpreter, '-c',
                'import numpy; print(numpy.__version__)'])
            if dependency.get('exit_code') != 0:
                skip(name, 'Final source requires NumPy, unavailable in this interpreter; no global install'); continue
        run_worker(name, [interpreter, '-B', '-O', source], inp, expected)


def local_managed_checks(inp, expected):
    ts = ROOT / 'runs/typescript/dist/worker.js'
    if NODE.is_file() and ts.is_file():
        command('node_existing_version', [NODE, '--version'])
        run_worker('typescript_existing_node_local', [NODE, ts], inp, expected)
    else: skip('typescript_existing_node_local', 'Existing Node or prebuilt worker.js unavailable')
    jar = ROOT / 'runs/kotlin/app.jar'; support = BASE / 'toolchains/kotlin/json-20260814.jar'
    if JAVA.is_file() and jar.is_file() and support.is_file():
        command('kotlin_existing_jdk_version', [JAVA, '-version'])
        rec = run_worker('kotlin_existing_jdk21_local', [JAVA, '-cp', str(jar) + os.pathsep + str(support),
                   'MainKt'], inp, expected)
        rec.update(runtime_contract='JVM JAR targeting Java21, requires compatible JRE21+',
                   android_apk='not_produced_or_tested', android_transferability='not_automatic')
        save()
    else: skip('kotlin_existing_jdk21_local', 'Existing JDK21 or prebuilt jars unavailable')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--after-stages-complete', action='store_true', required=True)
    parser.parse_args()
    # Require completed result summaries for every planned stage/language before CPU work.
    missing = []
    for lang in LANGS:
        for stage in ['initial', 'optimized', 'maintenance']:
            path = ROOT / 'results' / (lang + '_' + stage + '_perf.json')
            if not path.is_file() or 'summary' not in json.loads(path.read_text()): missing.append(str(path))
    if missing: raise SystemExit('Stages incomplete; refusing compatibility work: ' + ', '.join(missing))
    OUT.mkdir(exist_ok=False)  # Preserve previous evidence; operator archives it before rerunning.
    with (ROOT / 'results/.measure.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        inp, expected = tiny_dataset()
        save(); inspect_native_artifacts(); go_builds(); swift_checks(inp, expected); python_checks(inp, expected)
        local_managed_checks(inp, expected)
    print(OUT / 'results.json')


if __name__ == '__main__':
    main()
