#!/usr/bin/env python3
"""Unpack exact frozen fixtures; optionally regenerate eight-block long datasets."""
from pathlib import Path
import argparse,gzip,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lib.oracle import solve

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def unpack(destination):
 destination.mkdir(parents=True,exist_ok=True)
 for row in json.loads((ROOT/'data/fixtures.json').read_text(encoding='utf-8')):
  src=ROOT/row['gzip'];dst=destination/row['name']
  if digest(src)!=row['compressed_sha256']:raise ValueError('Compressed fixture hash mismatch: '+row['name'])
  if dst.exists():
   if digest(dst)!=row['sha256']:raise ValueError('Existing fixture differs: '+str(dst))
   continue
  temporary=dst.with_suffix(dst.suffix+'.tmp')
  with gzip.open(src,'rb') as inp,temporary.open('wb') as out:
   for chunk in iter(lambda:inp.read(1024*1024),b''):out.write(chunk)
  if digest(temporary)!=row['sha256']:raise ValueError('Fixture hash mismatch: '+row['name'])
  temporary.replace(dst)
 return destination

def long_files(destination):
 longdir=destination/'long_run';longdir.mkdir(exist_ok=True)
 manifest=json.loads((ROOT/'data/long_manifest.json').read_text(encoding='utf-8'))
 for row in manifest:
  kind=row['kind'];src=destination/(row['source_dataset']+'.jsonl')
  paths=[longdir/(kind+'_long.jsonl'),longdir/(kind+'_long.expected.jsonl')]
  if all(p.exists() for p in paths):
   for path,key in zip(paths,['input_sha256','expected_sha256']):
    if digest(path)!=row[key]:raise ValueError('Existing long fixture differs: '+path.name)
   continue
  if any(p.exists() for p in paths):raise ValueError('Partial long generation: preserve/inspect and move partial files before retry')
  temps=[p.with_suffix(p.suffix+'.tmp') for p in paths]
  with temps[0].open('w',encoding='utf8',newline='\n') as out,temps[1].open('w',encoding='utf8',newline='\n') as expected:
   for block in range(8):
    with src.open() as stream:
     for line in stream:
      if not line.strip():continue
      req=json.loads(line)
      if kind=='invoice':
       for event in req['events']:event['id']=f'block{block}:'+event['id']
      elif kind=='access_log':
       shift=block*100000;req['start_ms']+=shift;req['end_ms']+=shift
       for event in req['events']:event['ts_ms']+=shift
      else:req['samples']=[x+block*13 for x in req['samples']]
      out.write(json.dumps(req,separators=(',',':'),allow_nan=False)+'\n')
      expected.write(json.dumps(solve(req,True),separators=(',',':'),allow_nan=False)+'\n')
  for temp,path,key in zip(temps,paths,['input_sha256','expected_sha256']):
   if digest(temp)!=row[key]:raise ValueError('Regenerated long fixture hash mismatch: '+path.name)
   temp.replace(path)
 print('Long fixtures match all original input/output hashes.')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--long',action='store_true');p.add_argument('--output',type=Path,default=ROOT/'.work/data');args=p.parse_args()
 destination=unpack(args.output)
 if args.long:long_files(destination)
 print('Frozen fixtures verified in',destination)
if __name__=='__main__':main()
