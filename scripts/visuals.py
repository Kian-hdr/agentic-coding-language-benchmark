#!/usr/bin/env python3
"""Generate GitHub-native Mermaid charts from archived observations; standard library only."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.analyze import derive
NAMES={'typescript':'TypeScript','rust':'Rust','go':'Go','python':'Python','swift':'Swift','kotlin':'Kotlin/JVM','moonbit':'MoonBit','baml':'BAML'}
ORDER=list(NAMES)
def chart(title,labels,values,maximum,unit):
 return '\n'.join(['```mermaid','xychart-beta horizontal',f'    title "{title}"','    x-axis ['+', '.join(json.dumps(s) for s in labels)+']',f'    y-axis "{unit}" 0 --> {maximum}','    bar ['+', '.join(f'{v:.6f}' for v in values)+']','```'])
def generate():
 summary=derive();rows={(r['language'],r['workload']):r for r in summary['long']}
 parts=['# Visual guide to the measured results','','[Overview](../README.md) · [Tier list](TIER_LIST.md) · [Exact tables](../results/TABLES.md) · [Methods](METHODS.md)','','These charts are **native Mermaid blocks rendered by GitHub**, editable directly as text. There are no PNGs, rasterized charts, tracking chart services or client scripts to install. GitHub may provide pan/zoom controls; Markdown viewers without Mermaid can still read the source arrays and linked numeric tables.','','## CPU time: the complete worker, not a language speed limit','','Each chart uses the same category order and **0–7 CPU-second scale**. Lower is less CPU for that file; do not compare throughput across workloads with different item counts. Marks are medians of supported runs, not uncertainty intervals. `*` means one supported resource observation; all other plotted cells have two. Zerolang is omitted because it failed overall final eligibility, not plotted as zero.','','The observed min–max ranges immediately below each chart are the sample spread, **not confidence intervals**. Two repetitions cannot establish significance, p95/p99 or a steady-state asymptote.']
 specs=[('invoice','Invoice reconciliation','2,097,152 events'),('access_log','Access-log aggregation','2,097,152 events'),('telemetry','Rolling telemetry','16,777,216 samples')]
 chartdata={}
 for kind,title,count in specs:
  selected=[rows[lang,kind] for lang in ORDER];labels=[NAMES[r['language']]+(' *' if r['resource_n']==1 else '') for r in selected]
  parts += ['',f'### {title}', '',f'{count}; 4,096 requests; includes JSON parsing, file IO, startup/JIT and shutdown.','',chart(title+' | CPU seconds',labels,[r['cpu_seconds_median'] for r in selected],7,'CPU seconds'),'', '| Language | CPU median s | Observed min–max s | Resource n |','|---|---:|---:|---:|']
  for r,label in zip(selected,labels):parts.append(f"| {label} | {r['cpu_seconds_median']:.3f} | {r['cpu_seconds_min']:.3f}–{r['cpu_seconds_max']:.3f} | {r['resource_n']} |")
  chartdata[kind]=selected
 maxrss=[max(rows[lang,k]['peak_rss_mib_max'] for k,_,_ in specs) for lang in ORDER]
 minrss=[min(rows[lang,k]['peak_rss_mib_min'] for k,_,_ in specs) for lang in ORDER]
 parts += ['','## Peak resident memory','','Maximum supported process RSS across the three final workload kinds; the table also gives the full observed supported range. This is not an average, private memory, whole-fleet memory or billable reserved memory. The linear axis begins at zero; small native-worker bars are correctly small.','',chart('Maximum observed supported RSS',list(NAMES.values()),maxrss,350,'MiB'),'', '| Language | Observed RSS range MiB | Maximum MiB |','|---|---:|---:|']
 for lang,lo,hi in zip(ORDER,minrss,maxrss):parts.append(f'| {NAMES[lang]} | {lo:.1f}–{hi:.1f} | {hi:.1f} |')
 parts += ['','## Authoring effort','','This is the initial deep authoring turn only: one generated application per language, including service/tool latency. It is not a clean model-thinking or compiler timer. Optimization and maintenance costs must not be silently dropped from a full lifecycle comparison.','']
 metrics={lang:json.loads((ROOT/f'archive/deep/metrics/{lang}/initial_metrics.json').read_text(encoding='utf8')) for lang in [*ORDER,'zero']}
 parts += [chart('Initial deep authoring turn', [*NAMES.values(),'Zerolang'],[metrics[lang]['seconds'] for lang in [*ORDER,'zero']],450,'Elapsed seconds'),'','Python had the shortest observed initial turn. The four missing optimization receipts prevent a complete billed-cost ranking. Cached input is still a cost category; token units and all receipts are in [Results](RESULTS.md).','','## How the measurements reach the charts','','```mermaid','flowchart LR','    Raw[Archived raw observations] --> Gate{Correct and resource-supported?}','    Gate -->|Yes| Stats[Median and observed range]','    Gate -->|No| Exclude[Keep failure or exclusion visible]','    Stats --> Tables[JSON and CSV tables]','    Tables --> Charts[Native Mermaid charts]','    Tables --> Audit[Offline verification]','```','','## Rebuild these visuals','','```sh','python3 scripts/analyze.py --check','python3 scripts/visuals.py','python3 scripts/visuals.py --check','```','','`scripts/visuals.py` derives chart values directly from archived records through the same reviewed eligibility filters. `results/visual_data.json` retains the exact plotted data. It never assigns numeric scores to qualitative tiers. Native diagram syntax follows [GitHub documentation](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams); if a renderer changes, use the included tables rather than infer a different result.']
 chartdata['rss']=[{'language':lang,'min_mib':lo,'max_mib':hi} for lang,lo,hi in zip(ORDER,minrss,maxrss)]
 chartdata['authoring']=[{'language':lang,'seconds':metrics[lang]['seconds']} for lang in [*ORDER,'zero']]
 overview = '\n'.join([
  '**CPU and memory favor different implementations.** The invoice chart shows CPU for 2,097,152 events; the memory chart shows the maximum supported RSS across all three workloads. Lower is less resource use. These are different measures with different denominators.','',
  chart('Invoice reconciliation | CPU seconds', [NAMES[lang]+(' *' if rows[lang,'invoice']['resource_n']==1 else '') for lang in ORDER], [rows[lang,'invoice']['cpu_seconds_median'] for lang in ORDER],7,'CPU seconds'),'',
  'CPU marks are medians; n=2 except BAML invoice (*, n=1). Observed spread is in the visual guide and raw table, not a confidence interval. Zerolang is ineligible and is not plotted as zero.','',
  chart('Maximum observed supported RSS',list(NAMES.values()),maxrss,350,'MiB'),'',
  'Memory uses the maximum supported observation, not the mean. The linear axis starts at zero. Full supported RSS ranges and all exclusions are shown below and in the visual guide.'
 ])
 readme=(ROOT/'README.md').read_text(encoding='utf8')
 start='<!-- BEGIN GENERATED OVERVIEW -->';end='<!-- END GENERATED OVERVIEW -->'
 assert readme.count(start)==readme.count(end)==1
 readme=readme.split(start)[0]+start+'\n'+overview+'\n'+end+readme.split(end)[1]
 return {'README.md':readme,'docs/VISUAL_GUIDE.md':'\n'.join(parts)+'\n','results/visual_data.json':json.dumps({'classification':'native chart inputs; descriptive, not confidence estimates','data':chartdata},indent=2)+'\n'}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');a=p.parse_args()
 for rel,value in generate().items():
  path=ROOT/rel
  if a.check:
   if not path.exists() or path.read_text(encoding='utf8')!=value:raise SystemExit('Visual output differs: '+rel)
  else:path.write_text(value,encoding='utf8')
 print('Native Mermaid visuals '+('verified' if a.check else 'generated')+' from archived measurements.')
if __name__=='__main__':main()
