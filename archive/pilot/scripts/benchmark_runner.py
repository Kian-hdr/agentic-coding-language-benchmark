import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
CODEX = '{ORIGINAL_CODEX_APP}/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex'
FLAGS = ['--ignore-user-config', '--ephemeral', '--skip-git-repo-check',
         '--disable', 'apps', '--disable', 'plugins', '--disable', 'memories',
         '--disable', 'multi_agent', '--disable', 'multi_agent_v2',
         '--disable', 'hooks', '--disable', 'skill_search',
         '-s', 'workspace-write', '-m', 'gpt-6.1-sol',
         '-c', 'mcp_servers={}', '-c', 'model_reasoning_effort="medium"',
         '-c', 'approval_policy="never"', '--json']

INITIAL = '''Implement the three operations in SPEC.md in {language}.
This is a bounded language evaluation, not a production project. Work only in this
run directory. Read LANGUAGE.md and use its installed tools. Create executable
./run.sh REQUEST_FILE that prints exactly one response JSON object. All business
logic must be in {language}; wrappers may only transport IO and launch it.
Do not use other languages to implement computation. Do not access other runs,
benchmark evaluators, or sibling docs. Do not install packages, use the network,
delegate, create goals, or add features beyond the specification. You may inspect
the assigned toolchain's standard library and built-in help. Implement, run local
examples/tests, fix errors, and finish. You have 480 seconds maximum.
If requirements are infeasible, report the precise obstacle. Your final answer
must briefly state implementation and tests. Preserve your tests in this folder.
'''
EXTENSION = '''Extend your existing implementation with the following operation,
preserving all existing behavior. Keep the same language and run.sh protocol.
Input: {{"op":"merge","intervals":[[4,6],[1,3],[3,4]]}}.
Treat intervals as closed ranges; sort and merge overlaps or equal endpoints,
but do not merge separated integer ranges such as [1,2] and [3,4].
Output: {{"intervals":[[1,6]]}}. Any range with start greater than end returns
{{"error":"invalid_interval"}}. Empty input intervals returns {{"intervals":[]}}.
Integers and the required results fit signed 32-bit. Read your current code and
LANGUAGE.md, implement this change, test it and the prior operations, and finish.
Work only in this directory. No other-language computation, network, packages,
delegation, goals, or reading other run/evaluation directories. 240 seconds max.
'''

def phase(language, trial, phase_name):
    work = ROOT / 'runs' / f'{language}_{trial}'
    work.mkdir(parents=True, exist_ok=True)
    if phase_name == 'initial':
        spec = (ROOT / 'BENCHMARK.md').read_text().split('## Initial tasks\n')[1].split('## Later change')[0]
        (work / 'SPEC.md').write_text(spec)
        shutil.copyfile(ROOT / 'packets' / f'{language}.md', work / 'LANGUAGE.md')
        prompt = INITIAL.format(language=language)
    else:
        prompt = EXTENSION.format()
    (work / f'{phase_name}_prompt.txt').write_text(prompt)
    event_path = work / f'{phase_name}_events.jsonl'
    err_path = work / f'{phase_name}_stderr.log'
    timeout = 480 if phase_name == 'initial' else 240
    t = time.monotonic()
    with event_path.open('w') as out, err_path.open('w') as err:
        p = subprocess.Popen([CODEX, 'exec', *FLAGS, '-C', str(work), '-'],
                             stdin=subprocess.PIPE, stdout=out, stderr=err,
                             start_new_session=True, text=True)
        (work / f'{phase_name}_pid.txt').write_text(str(p.pid))
        timed_out = False
        try:
            p.communicate(prompt, timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(p.pid, signal.SIGTERM)
            try: p.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait()
    record = {'language':language, 'trial':trial, 'phase':phase_name,
              'model':'gpt-6.1-sol', 'reasoning':'medium',
              'seconds':round(time.monotonic()-t,3), 'exit_code':p.returncode,
              'timed_out':timed_out, 'usage':[], 'tool_calls':0, 'errors':[]}
    for line in event_path.read_text().splitlines():
        try: item=json.loads(line)
        except ValueError: continue
        if item.get('usage'): record['usage'].append(item['usage'])
        if item.get('type') == 'item.completed' and item.get('item',{}).get('type') == 'command_execution':
            record['tool_calls'] += 1
        if item.get('type') in ('error','turn.failed'): record['errors'].append(item)
    (work / f'{phase_name}_metrics.json').write_text(json.dumps(record,indent=2))
    snap = ROOT / 'snapshots' / f'{language}_{trial}_{phase_name}'
    shutil.copytree(work,snap,ignore=shutil.ignore_patterns('*events.jsonl','*stderr.log','*pid.txt'),dirs_exist_ok=True)
    print(json.dumps(record),flush=True)

if __name__ == '__main__':
    languages = sys.argv[1].split(',')
    phase_name = sys.argv[2] if len(sys.argv)>2 else 'initial'
    trial = int(sys.argv[3]) if len(sys.argv)>3 else 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(phase,lang,trial,phase_name) for lang in languages]
        for f in futures: f.result()
