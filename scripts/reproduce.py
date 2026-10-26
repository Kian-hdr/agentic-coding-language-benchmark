#!/usr/bin/env python3
"""Publication-time adapters: build and check archived implementations, never edit archive/."""
from pathlib import Path
import argparse,importlib.util,json,os,shlex,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.datasets import unpack,long_files
LANGS=['python','typescript','go','rust','swift','kotlin','moonbit','baml','zero','python_numpy']

def config():
 p=ROOT/'toolchains.local.json';return json.loads(p.read_text()) if p.exists() else {}
def tool(cfg,key,default):
 value=cfg.get(key,os.environ.get('BENCH_'+key.upper(),default))
 found=shutil.which(value)
 if not found:raise RuntimeError(f'Missing {key}: install the documented tool or set {key} in toolchains.local.json')
 return str(Path(found).absolute())
def work(lang,stage,phase='deep',trial=1):return ROOT/'.work'/phase/f'{lang}_{trial}'/stage

def source(lang,stage,phase,trial):
 if phase=='pilot':return ROOT/'archive/pilot/sources'/f'{lang}_{trial}_{stage}'
 if lang=='python_numpy':return ROOT/'archive/deep/supplementary/python_numpy'
 return ROOT/'archive/deep/sources'/lang/stage/'source'
def build(lang,stage,phase='deep',trial=1):
 cfg=config();src=source(lang,stage,phase,trial);dest=work(lang,stage,phase,trial)
 if not src.is_dir():raise RuntimeError('Missing snapshot: '+str(src))
 dest.mkdir(parents=True,exist_ok=True);shutil.copytree(src,dest,dirs_exist_ok=True)
 env=os.environ.copy()
 for key,upper in [('moon_home','MOON_HOME'),('baml_home','BAML_HOME'),('cargo_home','CARGO_HOME'),('rustup_home','RUSTUP_HOME'),('java_home','JAVA_HOME')]:
  if cfg.get(key):env[upper]=cfg[key]
 env['DO_NOT_TRACK']='1';commands=[];raw=phase=='pilot' and lang in ['go','rust','moonbit','zero']
 def find(name):
  matches=[p for p in dest.rglob(name) if not any(x in p.parts for x in ['vendor','target','_build'])]
  if len(matches)!=1:raise RuntimeError(f'Expected one {name}, got {len(matches)}')
  return matches[0]
 if lang in ['python','python_numpy']:
  interpreter=tool(cfg,'python_numpy' if lang=='python_numpy' else 'python',sys.executable)
  commands=[[interpreter,'-O','-m','py_compile',str(dest/'main.py')]]
  runtime=[interpreter,'-O',str(dest/'main.py')]
 elif lang=='typescript':
  tsc=tool(cfg,'tsc','tsc');node=tool(cfg,'node','node')
  conf=json.loads((dest/'tsconfig.json').read_text());opts=conf.setdefault('compilerOptions',{})
  if cfg.get('node_types'):opts['typeRoots']=[cfg['node_types']]
  else:opts.pop('typeRoots',None)
  opts['outDir']='dist';(dest/'tsconfig.json').write_text(json.dumps(conf,indent=2)+'\n')
  commands=[[tsc,'-p',str(dest/'tsconfig.json')]];runtime=[node,str(dest/'dist'/('worker.js' if phase=='deep' else 'main.js'))]
 elif lang=='go':
  commands=[[tool(cfg,'go','go'),'build','-trimpath','-ldflags=-s -w','-o',str(dest/'program'),str(dest/'main.go')]]
  env.update(GOTOOLCHAIN='local',GOCACHE=str(ROOT/'.work/go_cache'));runtime=[str(dest/'program')]
 elif lang=='rust':
  conf=dest/'.cargo/config.toml'
  if conf.exists():conf.unlink() # disposable copied config; preserve archived source
  if cfg.get('rust_vendor'):
   conf.parent.mkdir(exist_ok=True);conf.write_text('[source.crates-io]\nreplace-with="vendored-sources"\n[source.vendored-sources]\ndirectory='+json.dumps(cfg['rust_vendor'])+'\n')
  args=[tool(cfg,'cargo','cargo'),'build','--release']
  if (dest/'Cargo.lock').exists():args+=['--locked']
  if cfg.get('rust_vendor'):args+=['--offline']
  commands=[args];runtime=[str(dest/'target/release/agent_benchmark')]
 elif lang=='swift':
  compiler=tool(cfg,'swiftc','swiftc');commands=[[compiler,'-O','-whole-module-optimization',str(dest/'main.swift'),'-o',str(dest/'program')]];runtime=[str(dest/'program')]
 elif lang=='kotlin':
  jar=cfg.get('json_jar',os.environ.get('BENCH_JSON_JAR',''))
  if not Path(jar).is_file():raise RuntimeError('Set json_jar to org.json 20260814 jar (see toolchain guide)')
  main=find('Main.kt');commands=[[tool(cfg,'kotlinc','kotlinc'),str(main),'-jvm-target','21','-classpath',jar,'-include-runtime','-d',str(dest/'app.jar')]]
  runtime=[tool(cfg,'java','java'),'-cp',str(dest/'app.jar')+os.pathsep+jar,'MainKt']
 elif lang=='moonbit':
  project=dest if phase=='deep' else dest/'solution'
  if cfg.get('moon_deps'):
   link=project/'.mooncakes'
   if not link.exists():link.symlink_to(cfg['moon_deps'],target_is_directory=True)
  args=[tool(cfg,'moon','moon'),'-C',str(project),'build','--release','--target','native']
  if cfg.get('moon_deps'):args+=['--frozen']
  commands=[args];runtime=[str(project/'_build/native/release/build/cmd/main/main.exe')]
 elif lang=='baml':
  commands=[[tool(cfg,'baml','baml'),'--agent-skill-check','off','--directory',str(dest),'pack','main','--output',str(dest/'program')]]
  runtime=[str(dest/'program')]+(['--path'] if phase=='pilot' else [])
 else:
  if not (dest/'zero.graph').exists():raise RuntimeError('Canonical Zero graph absent in this historical snapshot; see provenance gaps. Do not reconstruct silently.')
  commands=[[tool(cfg,'zero','zero'),'build','--profile','release-fast','--out',str(dest/'program'),str(dest)]];runtime=[str(dest/'program')]
 start=time.monotonic();builds=[]
 for cmd in commands:
  run=subprocess.run(cmd,cwd=dest,env=env,capture_output=True,text=True,timeout=300)
  builds.append({'command':cmd,'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
  if run.returncode:
   (dest/'publication_build.json').write_text(json.dumps(builds,indent=2));raise RuntimeError('Build failed; see '+str(dest/'publication_build.json'))
 # Record version evidence for new rebuild separately; not original timing metadata.
 for key in ['PATH','MOON_HOME','BAML_HOME','CARGO_HOME','RUSTUP_HOME','JAVA_HOME','DO_NOT_TRACK']:
  if env.get(key) is not None:pass
 wrapper=dest/'publication_worker.sh'
 lines=['#!/bin/sh','set -eu']
 for key in ['MOON_HOME','BAML_HOME','CARGO_HOME','RUSTUP_HOME','JAVA_HOME','DO_NOT_TRACK']:
  if env.get(key) is not None:lines.append('export '+key+'='+shlex.quote(env[key]))
 invocation='exec '+' '.join(shlex.quote(x) for x in runtime)+' "$@"'
 if lang=='zero' and phase=='deep':invocation+=' > "$2"'
 lines.append(invocation);wrapper.write_text('\n'.join(lines)+'\n');wrapper.chmod(0o755)
 meta={'classification':'publication-time portable adapter; not historical launcher/timing','language':lang,'stage':stage,'phase':phase,'trial':trial,'seconds':time.monotonic()-start,'commands':builds,'runtime':runtime,'raw_json_argument':raw}
 (dest/'publication_build.json').write_text(json.dumps(meta,indent=2)+'\n');print('Built',phase,lang,stage,'in',dest)
 return wrapper

def execute(args):
 if os.name!='posix':raise RuntimeError('Execution adapter currently requires POSIX; offline evidence/analysis works on other platforms.')
 from lib import measurement as m
 dest=work(args.language,args.stage,args.phase,args.trial);wrapper=dest/'publication_worker.sh'
 if not wrapper.exists():raise RuntimeError('Build first with the same phase/stage/trial')
 out=dest/'new_results';out.mkdir(exist_ok=True)
 if args.phase=='pilot':
  if args.action!='validate':raise RuntimeError('Pilot perf: use archived protocol; this adapter currently replays correctness only.')
  from lib.pilot_oracle import cases,equivalent
  metadata=json.loads((dest/'publication_build.json').read_text());records=[]
  for i,(group,req,expected) in enumerate(cases(args.stage=='extension')):
   inp=out/f'case_{i:03d}.json';inp.write_text(json.dumps(req))
   arg=json.dumps(req) if metadata['raw_json_argument'] else str(inp)
   proc=subprocess.run([str(wrapper),arg],cwd=dest,capture_output=True,text=True,timeout=args.timeout)
   try:actual=json.loads(proc.stdout)
   except ValueError:actual=None
   records.append({'case':i,'group':group,'correct':proc.returncode==0 and equivalent(actual,expected),'returncode':proc.returncode})
  report={'classification':'new publication-adapter rerun, not original observations','records':records,'passed':sum(r['correct'] for r in records),'total':len(records)}
 else:
  data=unpack(ROOT/'.work/data');index=json.loads((ROOT/'data/index.json').read_text())
  if args.long:long_files(data)
  if args.action=='validate':selected=[r for r in index if r['kind']=='validation' and args.stage in r['stages']]
  elif args.long:selected=[{'name':r['name'],'input':'long_run/'+r['name']+'.jsonl','expected':'long_run/'+r['name']+'.expected.jsonl','expected_maintenance':'long_run/'+r['name']+'.expected.jsonl','requests':r['requests']} for r in json.loads((ROOT/'data/long_manifest.json').read_text())]
  else:selected=[r for r in index if r['size'] in ['medium','large','empty'] and args.stage in r['stages']]
  records=[];m.TIMEOUT_SECONDS=args.timeout
  for rep in range(1 if args.action=='validate' else args.repetitions):
   for row in selected:
    prefix=out/f"{row['name']}_{rep}";output=prefix.with_suffix('.output.jsonl')
    inp=data/row['input'];expected=data/row['expected_maintenance' if args.stage=='maintenance' else 'expected']
    if args.action=='perf':m.warm_file(inp)
    result=m.run_worker(wrapper,inp,output,prefix.with_suffix('.stdout.log'),prefix.with_suffix('.stderr.log'))
    result.update(m.compare_output(output,expected,row['requests']));result['dataset']=row['name'];result['repetition']=rep
    result['valid']=result.get('exit_code')==0 and not result.get('timed_out') and result.get('correct');records.append(result)
  report={'classification':'new publication-adapter rerun, not original observations','language':args.language,'stage':args.stage,'records':records,'passed':sum(r['valid'] for r in records),'total':len(records)}
 (out/(args.action+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='records'}));return report['passed']==report['total']
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['build','validate','perf']);p.add_argument('language',choices=LANGS);p.add_argument('--stage',default='maintenance',choices=['initial','optimized','maintenance','extension']);p.add_argument('--phase',default='deep',choices=['deep','pilot']);p.add_argument('--trial',type=int,choices=[1,2],default=1);p.add_argument('--repetitions',type=int,default=5);p.add_argument('--timeout',type=float,default=30);p.add_argument('--long',action='store_true');args=p.parse_args()
 if args.phase=='pilot' and args.stage not in ['initial','extension']:p.error('Pilot needs --stage initial or extension')
 if args.phase=='deep' and args.stage=='extension':p.error('Deep stages are initial/optimized/maintenance')
 if args.language=='python_numpy' and (args.phase!='deep' or args.stage!='maintenance'):p.error('NumPy is final deep supplementary only')
 if args.action=='build':build(args.language,args.stage,args.phase,args.trial)
 else:
  import fcntl
  (ROOT/'.work').mkdir(exist_ok=True)
  with (ROOT/'.work/measurement.lock').open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   if not execute(args):raise SystemExit(1)
if __name__=='__main__':main()
