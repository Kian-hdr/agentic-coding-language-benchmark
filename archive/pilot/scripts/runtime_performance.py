"""End-to-end process measurements, not intrinsic language throughput."""
import json
import os
from pathlib import Path
import random
import statistics
import signal
import subprocess
import time
from evaluate import ROOT, equivalent, ledger, topo, merge

def workloads():
    rng=random.Random(7126)
    jobs=[]
    for n in [100,1000,5000]:
        entries=[{'id':str(i),'account':'acct'+str(rng.randrange(max(1,n//10))),'amount':rng.randrange(-50,51)} for i in range(n)]
        jobs.append((f'ledger_{n}',{'op':'ledger','entries':entries},ledger(entries)))
    nodes=[f'n{i:03d}' for i in range(100)]
    edges=[[nodes[i],nodes[j]] for i in range(100) for j in range(i+1,100) if rng.random()<0.03]
    jobs.append(('topo_100',{'op':'topo','nodes':nodes,'edges':edges},topo(nodes,edges)))
    ints=[[i,i+3] for i in range(0,10000,10)]
    rng.shuffle(ints)
    jobs.append(('merge_1000',{'op':'merge','intervals':ints},merge(ints)))
    return jobs

def run_all():
    output=[]
    folder=ROOT/'results'/'stress_inputs';folder.mkdir(exist_ok=True)
    for name,request,expected in workloads():
        path=folder/f'{name}.json';path.write_text(json.dumps(request))
        for lang in ['python','typescript','go','rust','swift','kotlin','moonbit','baml','zero']:
            for trial in [1,2]:
                work=ROOT/'runs'/f'{lang}_{trial}'
                times=[]; status='pass'; diagnostic=None
                for repetition in range(6):
                    t=time.perf_counter()
                    try:
                        proc=subprocess.Popen([str(work/'run.sh'),str(path)],cwd=work,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
                        try:
                            stdout,stderr=proc.communicate(timeout=10)
                        except subprocess.TimeoutExpired:
                            os.killpg(proc.pid,signal.SIGKILL)
                            proc.communicate()
                            raise
                        p=subprocess.CompletedProcess(proc.args,proc.returncode,stdout,stderr)
                        elapsed=time.perf_counter()-t
                        try:actual=json.loads(p.stdout)
                        except ValueError:actual=None
                        if p.returncode!=0 or not equivalent(actual,expected):
                            status='fail';diagnostic={'code':p.returncode,'stderr':p.stderr[-500:],'stdout':p.stdout[:150]};break
                        if repetition>0: times.append(elapsed)
                    except (OSError,subprocess.TimeoutExpired) as e:
                        status='fail';diagnostic=str(e);break
                r={'language':lang,'trial':trial,'workload':name,'status':status,
                   'median_seconds':statistics.median(times) if times else None,
                   'samples':times,'diagnostic':diagnostic}
                output.append(r); print(json.dumps(r),flush=True)
    (ROOT/'results'/'runtime_performance.json').write_text(json.dumps(output,indent=2))

if __name__=='__main__':run_all()
