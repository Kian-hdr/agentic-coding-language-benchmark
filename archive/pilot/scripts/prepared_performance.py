"""Prepared executable comparison: same model-authored sources, no business edits."""
import json
import os
from pathlib import Path
import statistics
import subprocess
import time
from runtime_performance import workloads
from evaluate import ROOT, equivalent

def prepare(lang,trial):
    work=ROOT/'runs'/f'{lang}_{trial}'
    out=ROOT/'prepared'/f'{lang}_{trial}';out.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy()
    build=None; raw=False
    if lang=='python':cmd=['{ORIGINAL_HOMEBREW}/bin/python3.14',str(work/'main.py')]
    elif lang=='typescript':cmd=['{ORIGINAL_HOMEBREW}/bin/node',str(work/'dist/main.js')]
    elif lang=='go':cmd=[str(work/'program')];raw=True
    elif lang=='swift':cmd=[str(work/'program')]
    elif lang=='kotlin':cmd=['{ORIGINAL_HOMEBREW}/opt/openjdk@21/bin/java','-cp',str(work/'app.jar')+':'+str(ROOT/'toolchains/kotlin/json-20260814.jar'),'MainKt']
    elif lang=='rust':
        env['RUSTUP_HOME']=str(ROOT/'toolchains/rust/rustup')
        env['CARGO_HOME']=str(ROOT/'toolchains/rust/cargo')
        env['PATH']=str(ROOT/'toolchains/rust/cargo/bin')+':'+env['PATH']
        build=[str(ROOT/'toolchains/rust/cargo/bin/cargo'),'build','--release','--offline','--locked']
        cmd=[str(work/'target/release/agent_benchmark')];raw=True
    elif lang=='moonbit':
        env['MOON_HOME']=str(ROOT/'toolchains/moonbit')
        env['PATH']=str(ROOT/'toolchains/moonbit/bin')+':'+env['PATH']
        build=[str(ROOT/'toolchains/moonbit/bin/moon'),'-C',str(work/'solution'),'build','--release','--target','native']
        cmd=[str(work/'solution/_build/native/release/build/cmd/main/main.exe')];raw=True
    elif lang=='baml':
        env['BAML_HOME']=str(ROOT/'toolchains/baml');env['DO_NOT_TRACK']='1'
        build=[str(ROOT/'toolchains/baml/bin/baml'),'--agent-skill-check','off','--directory',str(work),'pack','main','--output',str(out/'program')]
        cmd=[str(out/'program'),'--path']
    elif lang=='zero':
        build=[str(ROOT/'toolchains/zero/bin/zero'),'build','--out',str(out/'program'),str(work)]
        cmd=[str(out/'program')];raw=True
    if build:
        t=time.perf_counter()
        p=subprocess.run(build,cwd=work,env=env,capture_output=True,text=True,timeout=120)
        (out/'build.json').write_text(json.dumps({'command':build,'seconds':time.perf_counter()-t,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr},indent=2))
        if p.returncode:raise RuntimeError(p.stderr[-800:])
    return work,env,cmd,raw

results=[]
for lang in ['python','typescript','go','rust','swift','kotlin','moonbit','baml','zero']:
    for trial in [1,2]:
        try:work,env,cmd,raw=prepare(lang,trial)
        except Exception as e:
            results.append({'language':lang,'trial':trial,'error':str(e)});continue
        for name,request,expected in workloads():
            if name not in ['ledger_1000','topo_100','merge_1000']:continue
            path=ROOT/'results/stress_inputs'/f'{name}.json'
            arg=json.dumps(request) if raw else str(path)
            samples=[];ok=True;error=None
            for rep in range(6):
                t=time.perf_counter()
                try:
                    p=subprocess.run(cmd+[arg],cwd=work,env=env,capture_output=True,text=True,timeout=10)
                except (OSError,subprocess.TimeoutExpired) as e:
                    ok=False;error=str(e);break
                elapsed=time.perf_counter()-t
                try:actual=json.loads(p.stdout)
                except ValueError:actual=None
                if p.returncode or not equivalent(actual,expected):
                    ok=False;error={'exit_code':p.returncode,'stdout':p.stdout[:300],'stderr':p.stderr[-500:]};break
                if rep:samples.append(elapsed)
            row={'language':lang,'trial':trial,'workload':name,'ok':ok,'command':cmd,'raw_json_argument':raw,
                 'median_seconds':statistics.median(samples) if samples else None,'samples':samples,'error':error}
            results.append(row);print(json.dumps(row),flush=True)
(ROOT/'results/prepared_performance.json').write_text(json.dumps(results,indent=2))
