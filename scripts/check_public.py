#!/usr/bin/env python3
"""Bounded publication checks for tracked/staged public files; not a security certification."""
from pathlib import Path
import json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
IGNORED={'.git','.work','.toolchains','__pycache__'}
def files():
 try:
  p=subprocess.run(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT,capture_output=True,check=True)
  paths=[ROOT/s for s in p.stdout.decode().split('\0') if s]
  if paths:return paths
 except (OSError,subprocess.CalledProcessError):pass
 return [p for p in ROOT.rglob('*') if p.is_file() and not set(p.relative_to(ROOT).parts)&IGNORED and p.name!='toolchains.local.json']
def main():
 problems=[];total=0
 checks={
  'private_home':r'(?:/Users/|/home/)[A-Za-z0-9._-]+/',
  'private_company_context':r'CloudStorage[/]|Shared drives[/]|_Personal[_]Vault|\.codex[/]auth\.json',
  'credential_pattern':r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,}|sk-(?:proj-)?[A-Za-z0-9_-]{32,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)',
  'private_account_identifier':r'(?i)[A-Za-z0-9._%+-]+@(?:gmail\.com|outlook\.com|hotmail\.com)',
 }
 for path in files():
  rel=str(path.relative_to(ROOT));total+=1
  if path.stat().st_size>=95_000_000:problems.append((rel,'oversize_git_blob'))
  if path.is_symlink():problems.append((rel,'unexpected_symlink'))
  if path.name=='toolchains.local.json' or path.name.endswith('_events.jsonl') or path.name.startswith('.env'):problems.append((rel,'excluded_private_file'))
  if path.suffix=='.gz':continue
  try:text=path.read_text(encoding='utf-8')
  except UnicodeDecodeError:
   if path.name=='zero.graph':text=path.read_bytes().decode('latin1')
   else:problems.append((rel,'unexpected_binary'));continue
  for label,pattern in checks.items():
   if re.search(pattern,text):problems.append((rel,label))
 # Link checking applies to maintained public-facing docs, not path-redacted historical snapshots.
 for path in [ROOT/'README.md',*(ROOT/'docs').glob('*.md')]:
  if not path.exists():continue
  for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
   if target.startswith(('https:','http:','mailto:','#')):continue
   dest=target.split('#',1)[0]
   if dest and not (path.parent/dest).exists():problems.append((str(path.relative_to(ROOT)),'missing_link:'+dest))
 if problems:
  print(json.dumps({'public_checks':'FAIL','findings':problems},indent=2));raise SystemExit(1)
 print(json.dumps({'public_checks':'PASS','files_checked':total,'note':'Pattern checks and maintained-doc links; not proof of absence of every secret.'}))
if __name__=='__main__':main()
