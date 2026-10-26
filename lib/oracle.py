import json
import math
from pathlib import Path
import random

ROOT=Path(__file__).resolve().parent
WS=' \t\n\r\v\f'

def invoice(req,maintenance=False):
    seen=set();customers={};accepted=duplicates=ignored=rejected=0
    gross=refund=fees=0;with_fee=maintenance and 'fee_bps' in req
    bps=req.get('fee_bps',0) if with_fee else 0
    for e in req['events']:
        if e['id'] in seen:duplicates+=1;continue
        seen.add(e['id']);name=e['customer'].strip(WS);amount=e['amount_cents'];status=e['status']
        if not name or amount<0 or status not in ['paid','refund','pending','void']:
            rejected+=1;continue
        if status in ['pending','void']:ignored+=1;continue
        accepted+=1
        row=customers.setdefault(name,{'customer':name,'gross_cents':0,'refund_cents':0,'net_cents':0,'count':0})
        row['count']+=1
        if with_fee:row.setdefault('fee_cents',0)
        if status=='paid':
            f=(amount*bps+5000)//10000
            row['gross_cents']+=amount;gross+=amount;row['net_cents']+=amount-f
            if with_fee:row['fee_cents']+=f;fees+=f
        else:row['refund_cents']+=amount;refund+=amount;row['net_cents']-=amount
    result={'customers':[customers[k] for k in sorted(customers)],'accepted':accepted,
            'duplicates':duplicates,'ignored':ignored,'rejected':rejected,
            'gross_cents':gross,'refund_cents':refund,'net_cents':gross-refund-fees}
    if with_fee:result['fee_cents']=fees
    return result

def access_log(req):
    groups={};count=errors=total_bytes=0
    for e in req['events']:
        if not(req['start_ms']<=e['ts_ms']<req['end_ms']):continue
        route=e['route'].strip(WS);g=groups.setdefault(route,{'count':0,'errors':0,'total_bytes':0,'durations':[]})
        err=int(e['status']>=500);g['count']+=1;g['errors']+=err;g['total_bytes']+=e['bytes'];g['durations'].append(e['duration_us'])
        count+=1;errors+=err;total_bytes+=e['bytes']
    rows=[]
    for route,g in sorted(groups.items()):
        ds=sorted(g.pop('durations'));g.update(route=route,max_us=ds[-1],p95_us=ds[(95*len(ds)+99)//100-1]);rows.append(g)
    return {'routes':rows,'total_count':count,'total_errors':errors,'total_bytes':total_bytes}

def trunc(a,b):return (abs(a)//b)*(-1 if a<0 else 1)

def telemetry(req):
    xs=req['samples'];w=req['window']
    if w<=0 or w>len(xs):return {'error':'invalid_window'}
    total=sum(xs[:w]);av=[trunc(total,w)]
    for i in range(w,len(xs)):
        total+=xs[i]-xs[i-w];av.append(trunc(total,w))
    return {'count':len(av),'min':min(av),'max':max(av),'above':sum(a>req['threshold'] for a in av),
            'weighted_checksum':sum((i+1)*a for i,a in enumerate(av))}

def solve(req,maintenance=False):
    if req.get('op')=='invoice':return invoice(req,maintenance)
    if req.get('op')=='access_log':return access_log(req)
    if req.get('op')=='telemetry':return telemetry(req)
    return {'error':'unknown_op'}

def request(rng,kind,n,i):
    if kind=='invoice':
        es=[]
        for j in range(n):
            es.append({'id':f'e{rng.randrange(max(1,n*4//5))}',
                       'customer':rng.choice(['a','aa','b','Z','a10','a2',' customer_'+str(rng.randrange(64))+' ','\tX\r',' ']),
                       'amount_cents':rng.randrange(-10,50000001),
                       'status':rng.choices(['paid','refund','pending','void','bad'],[65,15,10,8,2])[0]})
        return {'op':kind,'events':es}
    if kind=='access_log':
        return {'op':kind,'start_ms':1000,'end_ms':9000,'events':[
            {'ts_ms':rng.randrange(0,10000),'route':rng.choice(['/a','/aa',' /api/orders ','/b','/v1/items/'+str(rng.randrange(30))]),
             'status':rng.choice([200,201,204,301,400,404,429,500,503]),'duration_us':rng.randrange(0,10000000),
             'bytes':rng.randrange(0,20000000)} for _ in range(n)]}
    return {'op':kind,'samples':[rng.randrange(-100000,100001) for _ in range(n)],
            'window':rng.choice([1,7,31,127,511]),'threshold':rng.randrange(-2000,2001)}

def generate():
    folder=ROOT/'datasets';folder.mkdir(exist_ok=True);index=[]
    def write(name,kind,size,requests,items=0,stages=None,crlf=False,unterminated=False):
        inp=folder/(name+'.jsonl');expected=folder/(name+'.expected.jsonl');maint=folder/(name+'.maintenance.expected.jsonl')
        raw=[];e=[];m=[]
        for req in requests:
            if isinstance(req,str):
                raw.append(req)
                if not req.strip():continue
                try:obj=json.loads(req,parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
                except ValueError:
                    e.append({'error':'invalid_json'});m.append({'error':'invalid_json'});continue
            else:raw.append(json.dumps(req,separators=(',',':')));obj=req
            e.append(solve(obj));m.append(solve(obj,True))
        sep='\r\n' if crlf else '\n'
        inp.write_text(sep.join(raw)+('' if unterminated or not raw else sep))
        expected.write_text(''.join(json.dumps(x,separators=(',',':'))+'\n' for x in e))
        maint.write_text(''.join(json.dumps(x,separators=(',',':'))+'\n' for x in m))
        index.append({'name':name,'input':str(inp),'expected':str(expected),'expected_maintenance':str(maint),
                      'items':items,'requests':len(e),'kind':kind,'size':size,'stages':stages or ['initial','optimized','maintenance']})
    rng=random.Random(271026)
    validation=[]
    for kind in ['invoice','access_log','telemetry']:
        for i in range(20):validation.append(request(rng,kind,rng.randrange(1,80) if kind!='telemetry' else rng.randrange(512,800),i))
    validation.extend([{'op':'invoice','events':[]},{'op':'access_log','start_ms':0,'end_ms':0,'events':[]},
                       {'op':'telemetry','samples':[],'window':1,'threshold':0},
                       {'op':'telemetry','samples':[-2,5,8,1],'window':2,'threshold':3},
                       {'op':'telemetry','samples':[-5,-4],'window':1,'threshold':-5},
                       {'op':'telemetry','samples':[1,2],'window':0,'threshold':0},
                       {'op':'invoice','events':[{'id':'1','customer':'aa','amount_cents':5000000000,'status':'paid'},
                                               {'id':'1','customer':'','amount_cents':-5,'status':'bad'},
                                               {'id':'2','customer':'b','amount_cents':1,'status':'refund'}]},
                       'not json','{"op":',{'op':'nope'},'','   '])
    validation.extend([
        {'op':'invoice','events':[{'id':'first','customer':'x','amount_cents':-1,'status':'paid'}, {'id':'first','customer':'x','amount_cents':5,'status':'paid'}]},
        {'op':'invoice','events':[{'id':'huge','customer':'large','amount_cents':4503599627370,'status':'paid'}]},
        {'op':'access_log','start_ms':10,'end_ms':20,'events':[{'ts_ms':10,'route':' /a ','status':500,'duration_us':1,'bytes':4503599627370},{'ts_ms':20,'route':' /a ','status':200,'duration_us':99,'bytes':1}]},
        {'op':'telemetry','samples':[4503599627370,-4503599627370,3,-4],'window':2,'threshold':0},
        '{"op":"telemetry","samples":[NaN],"window":1,"threshold":0}',
        '{"op":"telemetry","samples":[Infinity],"window":1,"threshold":0}',
        {'op':'invoice','events':[{'id':'long','customer':'a'*90000,'amount_cents':1,'status':'paid'}]},
    ])
    validation += [validation[3],validation[2],validation[3]]
    write('validation','validation','mixed',validation)
    write('formatting','validation','mixed',validation[-14:],crlf=True,unterminated=True)
    fee=[]
    for bps in [0,1,10,1000]:
        for i in range(10):
            q=request(rng,'invoice',rng.randrange(1,100),i);q['fee_bps']=bps;fee.append(q)
    fee.extend([{'op':'invoice','fee_bps':100,'events':[{'id':'a','customer':'a','amount_cents':50,'status':'paid'},{'id':'b','customer':'b','amount_cents':49,'status':'paid'}]},
                {'op':'invoice','fee_bps':0,'events':[]}])
    interleaved=[]
    for q in fee:
        old=dict(q);old.pop('fee_bps',None)
        interleaved.extend([q,old,q])
    fee=interleaved
    write('fee_validation','validation','mixed',fee,stages=['maintenance'])
    safe=2**53-1
    holdout=[
        {'op':'invoice','events':[{'id':'boundary','customer':'aa','amount_cents':safe-1,'status':'paid'},{'id':'zero','customer':'b','amount_cents':0,'status':'refund'}]},
        {'op':'access_log','start_ms':0,'end_ms':1,'events':[{'ts_ms':0,'route':'/boundary','status':500,'duration_us':safe-2,'bytes':safe-1}]},
        {'op':'telemetry','samples':[safe-10,-safe+10,1,-1],'window':2,'threshold':0},
    ]
    write('numeric_holdout','validation','mixed',holdout,stages=['maintenance'])
    write('empty','empty','empty',[])
    for kind in ['invoice','access_log','telemetry']:
        for size,reps in [('small',8),('medium',64),('large',512)]:
            n=512 if kind!='telemetry' else 4096
            qs=[request(rng,kind,n,i) for i in range(reps)]
            write(f'{kind}_{size}',kind,size,qs,items=n*reps)
    (folder/'index.json').write_text(json.dumps(index,indent=2))
    print('datasets',len(index),'bytes',sum(Path(x['input']).stat().st_size for x in index))

if __name__=='__main__':generate()
