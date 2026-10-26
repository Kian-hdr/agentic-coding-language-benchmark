import json
from pathlib import Path
import statistics
ROOT=Path(__file__).resolve().parent
langs=['python','typescript','go','rust','swift','kotlin','moonbit','baml','zero']
rows=[]
for lang in langs:
    row={'language':lang,'trials':[]}
    for trial in [1,2]:
        t={'trial':trial,'phases':{}}
        for phase in ['initial','extension']:
            base=ROOT/'runs'/f'{lang}_{trial}'
            m=base/f'{phase}_metrics.json'
            e=ROOT/'results'/f'{lang}_{trial}_{phase}_evaluation.json'
            if not m.exists():continue
            data=json.loads(m.read_text())
            p={k:data[k] for k in ['seconds','timed_out','exit_code','tool_calls']}
            p['usage_reported']=bool(data['usage'])
            for name in ['input_tokens','cached_input_tokens','output_tokens','reasoning_output_tokens']:
                p[name]=sum(u.get(name,0) for u in data['usage'])
            p['uncached_input_tokens']=max(0,p['input_tokens']-p['cached_input_tokens'])
            commands=[]
            for l in (base/f'{phase}_events.jsonl').read_text().splitlines():
                try:x=json.loads(l)
                except ValueError:continue
                if x.get('type')=='item.completed' and x.get('item',{}).get('type')=='command_execution':commands.append(x['item'])
            p['failed_commands']=sum(c.get('exit_code') not in [None,0] for c in commands)
            if e.exists():
                er=json.loads(e.read_text())
                p.update(passed=er['passed'],planned=er['planned'],process_median_seconds=er['median_process_seconds'])
            t['phases'][phase]=p
        row['trials'].append(t)
    completed=[t for t in row['trials'] if all(k in t['phases'] and 'passed' in t['phases'][k] for k in ['initial','extension'])]
    if completed:
        row['complete_trials']=len(completed)
        row['passed']=sum(p['passed'] for t in completed for p in t['phases'].values())
        row['planned']=sum(p['planned'] for t in completed for p in t['phases'].values())
        row['median_total_agent_seconds']=statistics.median(sum(p['seconds'] for p in t['phases'].values()) for t in completed)
        row['total_input_tokens']=sum(p['input_tokens'] for t in completed for p in t['phases'].values())
        row['total_cached_input_tokens']=sum(p['cached_input_tokens'] for t in completed for p in t['phases'].values())
        row['total_uncached_input_tokens']=sum(p['uncached_input_tokens'] for t in completed for p in t['phases'].values())
        row['total_output_tokens']=sum(p['output_tokens'] for t in completed for p in t['phases'].values())
        row['failed_commands']=sum(p['failed_commands'] for t in completed for p in t['phases'].values())
        row['tool_calls']=sum(p['tool_calls'] for t in completed for p in t['phases'].values())
        row['usage_complete']=all(p['usage_reported'] for t in completed for p in t['phases'].values())
    rows.append(row)
(ROOT/'results'/'summary.json').write_text(json.dumps(rows,indent=2))
for r in rows:
    if r.get('complete_trials'):
        print(r['language'],str(r['complete_trials'])+' trials',str(r['passed'])+'/'+str(r['planned']),round(r['median_total_agent_seconds'],1),'s',r['total_uncached_input_tokens'],'uncached input',r['total_output_tokens'],'output')
    else:print(r['language'],'pending')
