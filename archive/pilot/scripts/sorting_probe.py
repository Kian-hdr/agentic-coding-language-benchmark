import json
from pathlib import Path
import subprocess
from evaluate import ROOT,equivalent,ledger,topo
out=[]
folder=ROOT/'results/sorting_inputs';folder.mkdir(exist_ok=True)
requests=[{'op':'ledger','entries':[{'id':str(i),'account':name,'amount':1} for i,name in enumerate(['b','aa','a'])]},
          {'op':'topo','nodes':['b','aa','a'],'edges':[]}]
for language in ['python','typescript','go','rust','swift','kotlin','moonbit','baml','zero']:
 for trial in [1,2]:
  work=ROOT/'runs'/f'{language}_{trial}'
  for req in requests:
   p=folder/f'{req["op"]}.json';p.write_text(json.dumps(req))
   expected=ledger(req['entries']) if req['op']=='ledger' else topo(req['nodes'],req['edges'])
   proc=subprocess.run([str(work/'run.sh'),str(p)],cwd=work,capture_output=True,text=True,timeout=10)
   try:actual=json.loads(proc.stdout)
   except ValueError:actual=proc.stdout
   out.append({'language':language,'trial':trial,'operation':req['op'],'ok':proc.returncode==0 and equivalent(actual,expected),'expected':expected,'actual':actual,'exit_code':proc.returncode})
(ROOT/'results/sorting_probe.json').write_text(json.dumps(out,indent=2))
for r in out:
 if not r['ok']:print(json.dumps(r))
