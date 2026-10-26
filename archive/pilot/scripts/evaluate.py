import heapq
import json
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent

def equivalent(actual,expected):
    if isinstance(actual,bool) != isinstance(expected,bool): return False
    if isinstance(expected,dict):
        return isinstance(actual,dict) and actual.keys()==expected.keys() and all(equivalent(actual[k],v) for k,v in expected.items())
    if isinstance(expected,list):
        return isinstance(actual,list) and len(actual)==len(expected) and all(equivalent(a,b) for a,b in zip(actual,expected))
    return actual==expected

def ledger(entries):
    seen=set(); accounts={}
    for e in entries:
        if e['id'] in seen: continue
        seen.add(e['id'])
        account=e['account'].strip(' \t\r\n\v\f')
        if not account: return {'error':'empty_account'}
        value=accounts.setdefault(account,[0,0])
        value[0]+=e['amount']; value[1]+=1
    return {'accounts':[{'account':k,'balance':v[0],'count':v[1]} for k,v in sorted(accounts.items())], 'accepted':len(seen)}

def topo(nodes,edges):
    ns=set(nodes)
    if any(a not in ns or b not in ns for a,b in edges): return {'error':'unknown_node'}
    adj={n:set() for n in nodes}; degree={n:0 for n in nodes}
    for a,b in edges:
        if b not in adj[a]: adj[a].add(b); degree[b]+=1
    available=[n for n in nodes if degree[n]==0]; heapq.heapify(available); out=[]
    while available:
        n=heapq.heappop(available); out.append(n)
        for b in adj[n]:
            degree[b]-=1
            if degree[b]==0: heapq.heappush(available,b)
    return {'order':out} if len(out)==len(nodes) else {'error':'cycle'}

def merge(intervals):
    if any(a>b for a,b in intervals): return {'error':'invalid_interval'}
    out=[]
    for a,b in sorted(intervals):
        if out and a<=out[-1][1]: out[-1][1]=max(b,out[-1][1])
        else: out.append([a,b])
    return {'intervals':out}

def trunc(a,b):
    return (abs(a)//abs(b)) * (-1 if (a<0)!=(b<0) else 1)

def expression(rng,depth):
    if depth==0 or rng.random()<0.25:
        n=rng.randrange(0,25)
        return str(n),n
    if rng.random()<0.3:
        text,n=expression(rng,depth-1)
        signs=rng.choice(['-','+','--','-+-'])
        return signs+'('+text+')',n*((-1)**signs.count('-'))
    a,av=expression(rng,depth-1); b,bv=expression(rng,depth-1)
    op=rng.choice(['+','-','*','/'])
    if op=='/' and bv==0: b,bv='3',3
    value={'+':lambda:av+bv,'-':lambda:av-bv,'*':lambda:av*bv,'/':lambda:trunc(av,bv)}[op]()
    return '('+a+' '+op+' '+b+')',value

def cases(include_merge):
    rng=random.Random(261026)
    out=[]
    def add(group,req,expected): out.append((group,req,expected))
    for entries in [[],[{'id':'z','account':'a','amount':0}],
                    [{'id':'x','account':' A ','amount':5},{'id':'x','account':'','amount':99}],
                    [{'id':'x','account':' \t ','amount':5}],
                    [{'id':'x','account':'a','amount':5},{'id':'y','account':'a','amount':-5}]]:
        add('ledger',{'op':'ledger','entries':entries},ledger(entries))
    for _ in range(12):
        entries=[{'id':str(rng.randrange(15)), 'account':rng.choice(['a',' b ','A','c','\tz\n']), 'amount':rng.randrange(-100,101)} for j in range(rng.randrange(1,70))]
        add('ledger',{'op':'ledger','entries':entries},ledger(entries))
    graphs=[([],[]),(['b','a'],[]),(['a'],[['a','a']]),(['a','b'],[['a','b'],['a','b']]),(['a'],[['a','x']])]
    for _ in range(12):
        nodes=[chr(97+i) for i in range(rng.randrange(1,10))]; rng.shuffle(nodes)
        edges=[[a,b] for a in nodes for b in nodes if rng.random()<0.13]
        if edges and rng.random()<0.5: edges.extend(edges[:2])
        graphs.append((nodes,edges))
    for nodes,edges in graphs: add('topo',{'op':'topo','nodes':nodes,'edges':edges},topo(nodes,edges))
    for expr,value in [('1+2*3',7),('8/3/2',1),('-8/3',-2),('8/-3',-2),('--4',4),('-+-4',4),(' \t(5) \n',5),('0',0)]:
        add('calc',{'op':'calc','expr':expr},{'value':value})
    for _ in range(12):
        expr,value=expression(rng,3); add('calc',{'op':'calc','expr':expr},{'value':value})
    for expr in ['', '1+', '()', '2(3)', '1 2','2**3','1//2','x','1.5','(2+3','2+3)']:
        add('calc',{'op':'calc','expr':expr},{'error':'syntax'})
    for expr in ['1/0','4/(2-2)','-3 / +0']:
        add('calc',{'op':'calc','expr':expr},{'error':'division_by_zero'})
    add('unknown',{'op':'nope'},{'error':'unknown_op'})
    if include_merge:
        inputs=[[],[[1,2],[3,4]],[[4,6],[1,3],[3,4]],[[4,3]],[[2,2],[2,2]], [[-5,-1],[-1,0],[3,4]]]
        for _ in range(14):
            ints=[]
            for __ in range(rng.randrange(1,35)):
                a=rng.randrange(-100,101); ints.append([a,a+rng.randrange(0,30)])
            inputs.append(ints)
        for intervals in inputs: add('merge',{'op':'merge','intervals':intervals},merge(intervals))
    return out

def evaluate(language,trial,phase):
    work=ROOT/'runs'/f'{language}_{trial}'
    if not (work/f'{phase}_metrics.json').exists():
        raise RuntimeError(f'Refusing to evaluate unfinished {language} {trial} {phase}')
    target=work/'run.sh'
    results=[]
    input_dir=ROOT/'results'/'inputs'/f'{language}_{trial}_{phase}'
    input_dir.mkdir(parents=True,exist_ok=True)
    for i,(group,request,expected) in enumerate(cases(phase=='extension')):
        inp=input_dir/f'{i:03d}.json'; inp.write_text(json.dumps(request))
        t=time.monotonic()
        try:
            p=subprocess.run([str(target),str(inp)],cwd=work,capture_output=True,text=True,timeout=8)
            try: actual=json.loads(p.stdout)
            except ValueError: actual={'invalid_stdout':p.stdout[:1500]}
            ok=p.returncode==0 and equivalent(actual,expected)
            result={'case':i,'group':group,'ok':ok,'seconds':round(time.monotonic()-t,6),'returncode':p.returncode}
            if not ok: result.update(request=request,expected=expected,actual=actual,stderr=p.stderr[-1500:])
        except (OSError,subprocess.TimeoutExpired) as e:
            result={'case':i,'group':group,'ok':False,'seconds':round(time.monotonic()-t,6),'exception':str(e)}
        results.append(result)
        # An absent runner cannot improve by repeating a missing-file error.
        if not target.exists(): break
    counts={}
    for r in results:
        counts.setdefault(r['group'],[0,0]); counts[r['group']][1]+=1
        counts[r['group']][0]+=int(r['ok'])
    report={'language':language,'trial':trial,'phase':phase,'passed':sum(x['ok'] for x in results),
            'executed':len(results),'planned':len(cases(phase=='extension')),'groups':counts,
            'median_process_seconds':statistics.median(x['seconds'] for x in results),'cases':results}
    path=ROOT/'results'/f'{language}_{trial}_{phase}_evaluation.json'
    path.write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='cases'}),flush=True)

if __name__=='__main__':
    for language in sys.argv[1].split(','):
        evaluate(language,int(sys.argv[3]),sys.argv[2])
