import concurrent.futures
import json
import os
from pathlib import Path
import random
import subprocess
import time
from agent_runs import ROOT,run

LANGS=['python','typescript','go','rust','swift','kotlin','moonbit','baml','zero']
PY='/usr/bin/python3'

def wait_initial():
    for lang in LANGS:
        p=ROOT/'runs'/lang/'initial_metrics.json'
        while not p.exists():time.sleep(2)

def compile_all(stage):
    for lang in LANGS:
        work=ROOT/'runs'/lang
        out=ROOT/'results'/f'{lang}_{stage}_build.json'
        if out.exists():continue
        script=work/'build.sh';t=time.monotonic()
        try:
            p=subprocess.run(['/bin/sh',str(script)],cwd=work,capture_output=True,text=True,timeout=120)
            record={'exit_code':p.returncode,'seconds':time.monotonic()-t,'stdout':p.stdout[-8000:],'stderr':p.stderr[-8000:]}
        except (OSError,subprocess.TimeoutExpired) as e:record={'exit_code':None,'seconds':time.monotonic()-t,'error':str(e)}
        out.write_text(json.dumps(record,indent=2))

def check_all(stage):
    for lang in LANGS:
        target=ROOT/'results'/f'{lang}_{stage}_validate.json'
        if target.exists() and 'summary' in json.loads(target.read_text()):continue
        with (ROOT/'results'/f'{lang}_{stage}_validate.log').open('w') as out:
            subprocess.run([PY,str(ROOT/'measure.py'),lang,stage,'validate'],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)

def perf_all(stage):
    targets=[ROOT/'results'/f'{lang}_{stage}_perf.json' for lang in LANGS]
    def complete(p):
        if not p.exists():return False
        d=json.loads(p.read_text());s=d.get('summary',{})
        return bool(s) and s.get('pending',0)==0 and len(d.get('records',[]))==s.get('planned')
    if all(complete(p) for p in targets):return
    with (ROOT/'results'/f'{stage}_perf.log').open('w') as out:
        p=subprocess.run([PY,str(ROOT/'measure.py'),'all',stage,'perf'],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
        if p.returncode not in [0,1] or not all(complete(t) for t in targets):
            raise RuntimeError(f'Measurement infrastructure failed in {stage}; inspect stage log')

def feedback():
    for lang in LANGS:
        v=json.loads((ROOT/'results'/f'{lang}_initial_validate.json').read_text())
        p=json.loads((ROOT/'results'/f'{lang}_initial_perf.json').read_text())
        failures=[]
        for rec in v['records']:
            if rec.get('valid'):continue
            data={'dataset_type':rec.get('kind'),'error':rec.get('launch_error',rec.get('measurement_error')),'mismatches':rec.get('mismatches',[])[:3]}
            if rec.get('input'):
                lines=[l for l in Path(rec['input']).read_text().splitlines() if l.strip()]
                for m in data['mismatches']:
                    idx=m.get('response',1)-1
                    if idx<len(lines):m['input_excerpt']=lines[idx][:4000]
            failures.append(data)
        stats=[]
        for rec in p['records']:
            if rec.get('skipped'):continue
            stats.append({k:rec.get(k) for k in ['dataset','size','items','valid','cpu_seconds','elapsed_seconds','peak_rss_mib','cpu_seconds_per_million_input_items','timed_out']})
        build=json.loads((ROOT/'results'/f'{lang}_initial_build.json').read_text())
        (ROOT/'runs'/lang/'FEEDBACK.json').write_text(json.dumps({'validation_summary':v['summary'],'reproducible_build':build,'failures':failures,'runtime_observations':stats,'note':'These are local batch-worker results, not per-request latency or pure algorithm speed. Correctness first; do not hardcode examples.'},indent=2))

def model_stage(stage):
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        fs=[pool.submit(run,lang,stage) for lang in LANGS if not (ROOT/'runs'/lang/f'{stage}_metrics.json').exists()]
        for f in concurrent.futures.as_completed(fs):f.result()

if __name__=='__main__':
    wait_initial()
    compile_all('initial');check_all('initial');perf_all('initial');feedback()
    (ROOT/'results/initial_complete').write_text('complete\n')
    model_stage('optimized')
    compile_all('optimized');check_all('optimized');perf_all('optimized')
    (ROOT/'results/optimized_complete').write_text('complete\n')
    model_stage('maintenance')
    compile_all('maintenance');check_all('maintenance');perf_all('maintenance')
    (ROOT/'results/all_complete').write_text('complete\n')
