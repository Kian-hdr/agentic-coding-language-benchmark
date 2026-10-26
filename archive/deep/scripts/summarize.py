"""Recompute report tables from frozen measurements; never reruns candidates."""
import hashlib
import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent
LANGS = ['python', 'typescript', 'go', 'rust', 'swift', 'kotlin', 'moonbit', 'baml', 'zero']
NAMES = dict(zip(LANGS, ['Python', 'TypeScript', 'Go', 'Rust', 'Swift', 'Kotlin/JVM', 'MoonBit', 'BAML', 'Zerolang']))
KINDS = ['invoice', 'access_log', 'telemetry']

def read(path):
    return json.loads((ROOT / path).read_text())

def aggregate(rows):
    supported = [r for r in rows if r.get('valid') and r.get('resource_accounting_supported')]
    result = {'records': len(rows), 'correct': sum(bool(r.get('valid')) for r in rows),
              'resource_supported': len(supported)}
    for key in ['cpu_seconds', 'peak_rss_mib', 'elapsed_seconds']:
        values = [r[key] for r in supported]
        result[key] = {'median': median(values), 'min': min(values), 'max': max(values)} if values else None
    if supported and 'items' in supported[0]:
        values = [r['cpu_seconds'] * 1_000_000 / r['items'] for r in supported if r['items']]
        if values:
            result['cpu_seconds_per_million_items'] = median(values)
    return result

def main():
    result = {'classification': 'observed implementations, one generated application per language',
              'stages': {}, 'long_run': {}, 'agent': {}, 'numpy': {}, 'source_hashes': {}}
    for stage in ['initial', 'optimized', 'maintenance']:
        result['stages'][stage] = {}
        for lang in LANGS:
            perf = read(f'results/{lang}_{stage}_perf.json')
            validation = read(f'results/{lang}_{stage}_validate.json')
            build = read(f'results/{lang}_{stage}_build.json')
            result['stages'][stage][lang] = {
                'validation': validation['summary'], 'performance': perf['summary'],
                'build_seconds': build['seconds'], 'build_exit_code': build['exit_code'],
                'large': {kind: aggregate([r for r in perf['records'] if r['kind'] == kind and r['size'] == 'large']) for kind in KINDS}}
    long = read('results/long_run.json')
    result['long_run_status'] = long['summary']
    for lang in LANGS:
        result['long_run'][lang] = {kind: aggregate([r for r in long['records'] if r['language'] == lang and r['kind'] == kind]) for kind in KINDS}
        result['agent'][lang] = {}
        for stage in ['initial', 'optimized', 'maintenance']:
            metrics = read(f'runs/{lang}/{stage}_metrics.json')
            usage = metrics['usage']
            result['agent'][lang][stage] = {key: metrics[key] for key in ['seconds', 'timed_out', 'commands', 'failed_commands']}
            result['agent'][lang][stage]['usage_known'] = bool(usage)
            result['agent'][lang][stage]['usage'] = {key: sum(r.get(key, 0) for r in usage) for key in ['input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_output_tokens']} if usage else None
    numpy = read('results/numpy_reference.json')
    result['numpy'] = {'classification': numpy['classification'], 'valid': numpy['valid'], 'kinds': {kind: aggregate([r for r in numpy['records'] if r['kind'] == kind]) for kind in KINDS}}
    for path in sorted((ROOT / 'results').glob('*.json')):
        result['source_hashes'][str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    result['source_hashes']['compatibility/results.json'] = hashlib.sha256((ROOT / 'compatibility/results.json').read_bytes()).hexdigest()
    (ROOT / 'Summary.json').write_text(json.dumps(result, indent=2) + '\n')
    lines = ['# Recomputed measurement tables', '', 'CPU seconds include full worker lifetime. Cells require correct output and supported resource accounting. Two long-run repetitions, except marked n=1. RSS is process peak resident memory, not private/billable memory.', '',
             '| Language | Invoice CPU s | Access log CPU s | Telemetry CPU s | Peak RSS range MiB |', '|---|---:|---:|---:|---:|']
    for lang in LANGS:
        row = result['long_run'][lang]
        cells = [f"{row[k]['cpu_seconds']['median']:.3f}" + (' (n=1)' if row[k]['resource_supported'] == 1 else '') if row[k]['cpu_seconds'] else 'ineligible' for k in KINDS]
        memory = [row[k]['peak_rss_mib'][edge] for k in KINDS if row[k]['peak_rss_mib'] for edge in ['min', 'max']]
        mem = f'{min(memory):.1f}–{max(memory):.1f}' if memory else 'ineligible'
        lines.append('| ' + ' | '.join([NAMES[lang], *cells, mem]) + ' |')
    lines += ['', 'Invoice and access log each contain 2,097,152 events; telemetry contains 16,777,216 samples. Each file has 4,096 requests.', '', '| Language | Initial / maintenance seconds | Initial uncached input kTok | Initial cached input kTok | Initial output kTok | Optimization turn |', '|---|---:|---:|---:|---:|---|']
    for lang in LANGS:
        a = result['agent'][lang]; u = a['initial']['usage']
        lines.append(f"| {NAMES[lang]} | {a['initial']['seconds']:.1f} / {a['maintenance']['seconds']:.1f} | {(u['input_tokens']-u['cached_input_tokens'])/1000:.1f} | {u['cached_input_tokens']/1000:.1f} | {u['output_tokens']/1000:.1f} | {'timed out; usage unknown' if a['optimized']['timed_out'] else 'completed'} |")
    lines += ['', 'Token units are decimal. Cached input remains input and is not free. Missing receipts are unknown. Reasoning counters are retained in Summary.json; do not blindly add them to output if included by the provider.', '', '## Individual supported long-run observations', '', '| Language | Workload | CPU seconds | Peak RSS MiB |', '|---|---|---|---|']
    for lang in LANGS:
        for kind in KINDS:
            rows = [r for r in long['records'] if r['language'] == lang and r['kind'] == kind and r.get('valid') and r.get('resource_accounting_supported')]
            if rows:
                cpus = ', '.join(format(r['cpu_seconds'], '.4f') for r in rows)
                rss = ', '.join(format(r['peak_rss_mib'], '.1f') for r in rows)
                lines.append(f"| {NAMES[lang]} | {kind} | {cpus} | {rss} |")
    (ROOT / 'Measurement_Tables.md').write_text('\n'.join(lines) + '\n')
    print('Wrote Summary.json and Measurement_Tables.md')

if __name__ == '__main__':
    main()
