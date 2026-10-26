import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
from benchmark_runner import CODEX,FLAGS

INITIAL='''Implement SPEC.md in {language}, including all three application operations
and a persistent bulk-file worker. Read LANGUAGE.md for installed tool paths and
version-local IO APIs. The NEW SPEC.md overrides old protocol examples in LANGUAGE.
Create optimized build.sh and worker.sh INPUT_JSONL OUTPUT_JSONL. All computation,
JSON parsing and file reading/writing must be in {language}; no per-record child
process, no algorithm outsourcing. Build before finishing, run your own tests.
Work only in this directory and assigned toolchain docs/starters. Do not inspect
other runs, evaluator code, datasets or parent benchmark code. No internet,
package installation, goals, delegation or public deployment. Existing approved
JSON support and MoonBit official async IO are allowed. No other dependencies.
This is a bounded experiment, not a product. Implement robustly and efficiently
but prioritize correctness. Maximum 720 seconds. Report any unsupported capacity
or platform behavior honestly. Finish with brief build/test evidence.
'''
OPTIMIZE='''Read FEEDBACK.json and inspect your current implementation. You have 360
seconds to repair correctness failures and optimize CPU/memory use of the same
worker and operations. Preserve exact SPEC.md semantics and streaming file IO.
Prefer better algorithms and allocation behavior before micro-optimizations.
Do not hardcode responses or dataset patterns. You may use stdlib plus approved
JSON/IO dependencies already installed. Python may additionally use the preinstalled
NumPy environment described in LANGUAGE.md; disclose this native-library use.
No other languages for business computation, no external downloads/network,
delegation, goals or access to evaluator/other runs. Build optimized/release
artifacts and test your changes. Keep worker.sh interface unchanged.
'''
MAINTAIN='''Add a backwards-compatible invoice fee feature to the current worker.
If an invoice request includes optional integer fee_bps (0..1000), calculate
fee per accepted paid event as (amount_cents*fee_bps + 5000) / 10000 using integer
floor division (amounts nonnegative). Refunds have zero fee. Add fee_cents to
each customer row and top-level totals, and subtract fees in net_cents.
When fee_bps is ABSENT, preserve the exact old schema and behavior, including
no fee_cents fields. When present as zero, include fee_cents=0. All amounts
remain exactly representable within signed safe 53-bit range; intermediates
also fit. Preserve all other operations, recovery, and request isolation.
Maximum 240 seconds. Same dependency/scope rules. Build and test before ending.
'''

def run(language,stage):
    work=ROOT/'runs'/language;work.mkdir(parents=True,exist_ok=True)
    if stage=='initial':
        shutil.copyfile(ROOT/'SPEC.md',work/'SPEC.md')
        shutil.copyfile(ROOT/'packets'/f'{language}.md',work/'LANGUAGE.md')
    prompt={'initial':INITIAL.format(language=language),'optimized':OPTIMIZE,'maintenance':MAINTAIN}[stage]
    (work/f'{stage}_prompt.txt').write_text(prompt)
    limit={'initial':720,'optimized':360,'maintenance':240}[stage]
    start=time.monotonic();timed_out=False
    log=work/f'{stage}_events.jsonl'
    with log.open('w') as out,(work/f'{stage}_stderr.log').open('w') as err:
        p=subprocess.Popen([CODEX,'exec',*FLAGS,'-C',str(work),'-'],stdin=subprocess.PIPE,stdout=out,stderr=err,text=True,start_new_session=True)
        (work/f'{stage}_pid.txt').write_text(str(p.pid))
        try:p.communicate(prompt,timeout=limit)
        except subprocess.TimeoutExpired:
            timed_out=True;os.killpg(p.pid,signal.SIGTERM)
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
    record={'language':language,'stage':stage,'model':'gpt-6.1-sol','reasoning':'medium','seconds':time.monotonic()-start,'timed_out':timed_out,'exit_code':p.returncode,'usage':[],'commands':0,'failed_commands':0}
    for line in log.read_text().splitlines():
        try:x=json.loads(line)
        except ValueError:continue
        if x.get('usage'):record['usage'].append(x['usage'])
        if x.get('type')=='item.completed' and x.get('item',{}).get('type')=='command_execution':
            record['commands']+=1
            record['failed_commands']+=int(x['item'].get('exit_code') not in [0,None])
    (work/f'{stage}_metrics.json').write_text(json.dumps(record,indent=2))
    artifact=ROOT/'artifacts'/language/stage
    artifact.mkdir(parents=True,exist_ok=True)
    # Preserve authored source and metadata, excluding regenerable dependency/build trees.
    for f in work.rglob('*'):
        rel=f.relative_to(work)
        if any(s in rel.parts for s in ['target','_build','vendor','.mooncakes','.git','.module_cache','node_modules','__pycache__']):continue
        if f.is_file() and f.suffix in ['.py','.rs','.go','.ts','.swift','.kt','.baml','.mbt','.0','.sh','.toml','.json','.mod','.pkg']:
            dest=artifact/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
    print(json.dumps(record),flush=True)

if __name__=='__main__':
    langs=sys.argv[1].split(',');stage=sys.argv[2]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for f in concurrent.futures.as_completed([pool.submit(run,l,stage) for l in langs]):f.result()
