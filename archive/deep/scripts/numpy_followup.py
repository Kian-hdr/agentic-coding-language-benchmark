"""Exploratory native-kernel reference, not part of equal-budget nine-way trial."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import fcntl

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
from benchmark_runner import CODEX,FLAGS
import measure

def main():
    if not (ROOT/'results/followups_complete').exists():raise RuntimeError('Main experiments and compatibility must finish first')
    work=ROOT/'runs/python_numpy';work.mkdir(exist_ok=True)
    for name in ['main.py','build.py','build.sh','worker.sh','test_worker.py','SPEC.md']:
        src=ROOT/'runs/python'/name
        if src.exists():shutil.copy2(src,work/name)
    prompt='''This is a separately disclosed exploratory Python+NumPy reference,
not an equal-budget trial. Starting from the existing correct Python worker,
replace ONLY telemetry's numerical kernel with NumPy int64 vector operations
where helpful. Preserve exact integer semantics, truncation toward zero, and all
other behavior including invoice fee feature and streaming file IO. Avoid floats
for exact integer arithmetic. The original SPEC.md still governs the worker.
NumPy 2.5.4 is already installed in {ORIGINAL_BENCHMARK_ROOT}/deep_phase/toolchains/python/bin/python .
Use that interpreter in worker.sh; build.py may compile with the same interpreter.
Keep CLI worker.sh INPUT_JSONL OUTPUT_JSONL and build.sh. No other dependencies,
network, goals, delegation, cross-run/evaluator access or other changes. Test
your implementation and build before finishing. Maximum 180 seconds.
'''
    (work/'reference_prompt.txt').write_text(prompt)
    start=time.monotonic();timeout=False
    with (work/'reference_events.jsonl').open('w') as out,(work/'reference_stderr.log').open('w') as err:
        proc=subprocess.Popen([CODEX,'exec',*FLAGS,'-C',str(work),'-'],stdin=subprocess.PIPE,stdout=out,stderr=err,text=True,start_new_session=True)
        try:proc.communicate(prompt,timeout=180)
        except subprocess.TimeoutExpired:
            timeout=True;os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
    usage=[]
    for l in (work/'reference_events.jsonl').read_text().splitlines():
        try:e=json.loads(l)
        except ValueError:continue
        if e.get('usage'):usage.append(e['usage'])
    (work/'reference_metrics.json').write_text(json.dumps({'seconds':time.monotonic()-start,'exit_code':proc.returncode,'timed_out':timeout,'usage':usage,'classification':'extra targeted prompt, exploratory native-kernel reference'},indent=2))
    build=subprocess.run(['/bin/sh',str(work/'build.sh')],cwd=work,capture_output=True,text=True,timeout=120)
    (ROOT/'results/python_numpy_build.json').write_text(json.dumps({'exit_code':build.returncode,'stdout':build.stdout,'stderr':build.stderr},indent=2))
    subprocess.run(['/usr/bin/python3',str(ROOT/'measure.py'),'python_numpy','maintenance','validate'],cwd=ROOT)
    valid=json.loads((ROOT/'results/python_numpy_maintenance_validate.json').read_text())['summary']['all_valid']
    result={'classification':'exploratory extra-prompt reference; not equal-budget language result','valid':valid,'records':[]}
    if valid:
        original=json.loads((ROOT/'results/long_run.json').read_text())
        datasets=original.get('datasets',[])
        if isinstance(datasets,dict):datasets=list(datasets.values())
        measure.TIMEOUT_SECONDS=120
        with (ROOT/'results/.measure.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            folder=ROOT/'results/numpy_long';folder.mkdir(exist_ok=True)
            for d in datasets:
                source=Path(d.get('input',d.get('path','')));expected=Path(d['expected'])
                for rep in range(2):
                    stem=folder/(d.get('kind',d.get('name','workload'))+'_'+str(rep))
                    out=Path(str(stem)+'.output.jsonl')
                    measure.warm_file(source)
                    r=measure.run_worker(work/'worker.sh',source,out,Path(str(stem)+'.stdout'),Path(str(stem)+'.stderr'))
                    r.update(measure.compare_output(out,expected,d.get('requests')))
                    r.update(kind=d.get('kind'),items=d.get('items'),repetition=rep)
                    r['valid']=r.get('exit_code')==0 and not r.get('timed_out') and r.get('correct')
                    result['records'].append(r)
                    if not r['valid']:break
    (ROOT/'results/numpy_reference.json').write_text(json.dumps(result,indent=2))
    (ROOT/'results/numpy_complete').write_text('complete\n')

if __name__=='__main__':main()
