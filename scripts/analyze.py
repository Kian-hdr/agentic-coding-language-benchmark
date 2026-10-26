#!/usr/bin/env python3
"""Publication-time analysis of recorded results. No model or benchmark execution."""
from pathlib import Path
import argparse,csv,io,json,statistics
ROOT=Path(__file__).resolve().parents[1]
LANGS=['python','typescript','go','rust','swift','kotlin','moonbit','baml','zero']
KINDS=['invoice','access_log','telemetry']
def read(rel):return json.loads((ROOT/rel).read_text())
def derive():
 long=read('archive/deep/results/long_run.json'); rows=[]
 for lang in LANGS:
  eligible=next(x['eligible'] for x in long['eligibility'] if x['language']==lang)
  for kind in KINDS:
   raw=[r for r in long['records'] if r['language']==lang and r['kind']==kind]
   accepted=[r for r in raw if eligible and r.get('valid') and r.get('resource_accounting_supported')]
   row={'language':lang,'workload':kind,'eligible':eligible,'scheduled':len(raw),'correct':sum(bool(r.get('valid')) for r in raw),'resource_n':len(accepted)}
   for key in ['cpu_seconds','peak_rss_mib','elapsed_seconds']:
    values=[r[key] for r in accepted]
    for stat,fn in [('median',statistics.median),('min',min),('max',max)]:row[key+'_'+stat]=fn(values) if values else None
   row['cpu_seconds_per_million_items']=statistics.median(r['cpu_seconds']*1e6/r['items'] for r in accepted) if accepted else None
   rows.append(row)
 pilot=read('archive/pilot/results/summary.json')
 counts={'pilot_scored_turns':36,'deep_scored_turns':27,'main_turns':63,'pilot_passed_observations':sum(r['passed'] for r in pilot),'long':long['summary'],'long_supported_resource_records':sum(r['resource_n'] for r in rows)}
 return {'schema_version':1,'classification':'descriptive single-host generated-implementation results','counts':counts,'long':rows}
def rendered(summary):
 lines=['# Recomputed recorded long-run results','','These are observed generated implementations, not intrinsic language rankings. CPU includes parsing, file IO, startup/JIT and shutdown. RSS is process peak resident memory, not private/billable memory. Two scheduled repetitions per cell; resource_n excludes flagged process trees and ineligible programs.','','| Language | Workload | CPU median s | CPU min–max s | RSS min–max MiB | Resource n |','|---|---|---:|---:|---:|---:|']
 for r in summary['long']:
  if r['resource_n']:
   v=f"{r['cpu_seconds_median']:.6f}";rng=f"{r['cpu_seconds_min']:.6f}–{r['cpu_seconds_max']:.6f}";rss=f"{r['peak_rss_mib_min']:.3f}–{r['peak_rss_mib_max']:.3f}"
  else:v=rng=rss='ineligible'
  lines.append(f"| {r['language']} | {r['workload']} | {v} | {rng} | {rss} | {r['resource_n']} |")
 return '\n'.join(lines)+'\n'
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
 data=derive();csvbuf=io.StringIO(newline='');writer=csv.DictWriter(csvbuf,fieldnames=list(data['long'][0]),lineterminator='\n');writer.writeheader();writer.writerows(data['long'])
 outputs={'results/summary.json':json.dumps(data,indent=2,allow_nan=False)+'\n','results/long_run.csv':csvbuf.getvalue(),'results/TABLES.md':rendered(data)}
 for rel,text in outputs.items():
  path=ROOT/rel
  if args.check:
   if not path.is_file() or path.read_text()!=text:raise SystemExit('Derived output differs: '+rel)
  else:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
 print('Recorded analysis '+('verified' if args.check else 'generated')+'; no benchmark/model calls.')
if __name__=='__main__':main()
