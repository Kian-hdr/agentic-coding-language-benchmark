#!/usr/bin/env python3
"""Offline evidence integrity and completeness checks. No model calls or compilers."""
from pathlib import Path
import argparse,gzip,hashlib,json,math,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lib.oracle import solve
from scripts.analyze import derive
LANGS=['python','typescript','go','rust','swift','kotlin','moonbit','baml','zero']
def load(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def digest(data):return hashlib.sha256(data).hexdigest()
def equal(a,b):
 if isinstance(a,bool) or isinstance(b,bool):return type(a)==type(b) and a==b
 if isinstance(a,(int,float)) and isinstance(b,(int,float)):return math.isfinite(a) and math.isfinite(b) and a==b
 if type(a)!=type(b):return False
 if isinstance(a,dict):return a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
 if isinstance(a,list):return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
 return a==b

def full_fixtures(contents):
 assertions=0
 for entry in load('data/index.json'):
  raw=contents[entry['input']].decode();expected={False:[],True:[]}
  for line in raw.splitlines():
   if not line.strip():continue
   try:req=json.loads(line,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
   except ValueError:
    for value in expected.values():value.append({'error':'invalid_json'})
    continue
   for maintenance in expected:expected[maintenance].append(solve(req,maintenance))
  for maintenance,key in [(False,'expected'),(True,'expected_maintenance')]:
   recorded=[json.loads(x) for x in contents[entry[key]].decode().splitlines() if x.strip()]
   assert equal(recorded,expected[maintenance]),'Oracle differs: '+entry['name']+' '+key
   assert len(recorded)==entry['requests'];assertions+=len(recorded)
 return assertions

def verify(full=False):
 manifest=load('archive/export_manifest.json')
 for row in manifest['files']:
  assert digest((ROOT/row['public']).read_bytes())==row['public_sha256'],'Export hash: '+row['public']
 fixtures={}
 for row in load('data/fixtures.json'):
  packed=(ROOT/row['gzip']).read_bytes();assert digest(packed)==row['compressed_sha256']
  raw=gzip.decompress(packed);assert digest(raw)==row['sha256'] and len(raw)==row['bytes'];fixtures[row['name']]=raw
 pilot=[]
 for lang in LANGS:
  for trial in [1,2]:
   for stage,n in [('initial',69),('extension',89)]:
    row=load(f'archive/pilot/results/{lang}_{trial}_{stage}_evaluation.json')
    assert row['planned']==n and row['executed']==n and len(row['cases'])==n
    assert sum(bool(x['ok']) for x in row['cases'])==row['passed']==n
    metrics=load(f'archive/pilot/metrics/{lang}_{trial}/{stage}_metrics.json');assert metrics['model']=='gpt-6.1-sol'
    pilot.append(row)
 assert sum(x['passed'] for x in pilot)==2844
 for stage in ['initial','optimized','maintenance']:
  sequence=[]
  for lang in LANGS:
   for mode in ['validate','perf']:
    row=load(f'archive/deep/results/{lang}_{stage}_{mode}.json');summary=row['summary']
    assert summary.get('pending',summary['planned']-summary['attempted']-summary['skipped'])==0
    assert len(row['records'])==summary['planned']
    if lang!='zero':assert summary['all_valid']
    if mode=='perf':sequence.extend(r['global_sequence'] for r in row['records'])
   build=load(f'archive/deep/results/{lang}_{stage}_build.json')
   if lang!='zero':assert build['exit_code']==0
   metrics=load(f'archive/deep/metrics/{lang}/{stage}_metrics.json');assert metrics['model']=='gpt-6.1-sol'
   if metrics['timed_out']:assert not metrics['usage'],'Do not silently replace missing receipts'
  assert sorted(sequence)==list(range(297))
 long=load('archive/deep/results/long_run.json');assert len(long['records'])==54
 assert sum(bool(r.get('valid')) for r in long['records'])==48
 assert sum(bool(r.get('skipped')) for r in long['records'])==6
 assert all(r['language']=='zero' for r in long['records'] if r.get('skipped'))
 supported=[r for r in long['records'] if r.get('valid') and r.get('resource_accounting_supported')]
 assert len(supported)==46
 unsupported={(r['language'],r['kind'],r['repetition']) for r in long['records'] if r.get('valid') and not r.get('resource_accounting_supported')}
 assert unsupported=={('kotlin','telemetry',0),('baml','invoice',1)}
 assert len({(r['language'],r['kind'],r['repetition']) for r in long['records']})==54
 numpy=load('archive/deep/results/numpy_reference.json');assert numpy['valid'] and len(numpy['records'])==6
 assert all(r['valid'] and r['resource_accounting_supported'] for r in numpy['records'])
 result=derive();assert result['counts']['long_supported_resource_records']==46
 # Compare publication derivation against historical summary without trusting its resource logic.
 historical=load('archive/deep/reports/Summary.json')
 for row in result['long']:
  old=historical['long_run'][row['language']][row['workload']]
  assert old['resource_supported']==row['resource_n']
  if row['resource_n']:assert old['cpu_seconds']['median']==row['cpu_seconds_median']
 assertions=full_fixtures(fixtures) if full else 0
 return {'exported_files':len(manifest['files']),'frozen_files':len(fixtures),'pilot_observations':2844,'main_agent_turns':63,'deep_perf_scheduled':891,'long_correct':48,'long_resource_supported':46,'numpy_correct':6,'oracle_response_comparisons':assertions}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--full',action='store_true',help='also recompute oracle responses for every frozen base fixture');a=p.parse_args()
 print(json.dumps(verify(a.full),indent=2));print('Offline evidence verification PASS. This verifies archived observations, not independent model replication.')
if __name__=='__main__':main()
