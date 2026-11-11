#!/usr/bin/env python3
"""Conservative, read-only research project inventory and anomaly audit."""
import argparse, csv, datetime as dt, hashlib, json, os, re, stat
from pathlib import Path

LOG_EXT={'.log','.out','.err','.stderr','.stdout'}
DATA_EXT={'.csv','.tsv','.json','.jsonl'}
DOC_EXT={'.md','.txt'}
MODEL_EXT={'.pdb','.cif','.mmcif','.pt','.pth','.safetensors'}
PATTERNS=[('OOM',re.compile(r'out of memory|cuda out of memory|oom-kill|killed process',re.I)),('TRACEBACK',re.compile(r'Traceback \(most recent call last\)|^\s*(?:ValueError|RuntimeError|KeyError|AssertionError|FileNotFoundError):',re.I)),('NUMERIC',re.compile(r'\b(?:nan|inf|infinity)\b',re.I)),('FAIL',re.compile(r'\b(?:segmentation fault|fatal error|failed to converge)\b',re.I))]
IGNORE={'.git','.venv','venv','env','node_modules','__pycache__','.cache','site-packages'}

def sha256(path, limit):
    if path.stat().st_size>limit:return None
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def tail(path, limit=131072):
    with path.open('rb') as f:
        f.seek(0,2); size=f.tell(); f.seek(max(0,size-limit)); return f.read().decode('utf-8','replace').splitlines()

def scan_file(path, max_hash, max_data):
    s=path.stat(); entry={'path':str(path),'bytes':s.st_size,'modified_utc':dt.datetime.fromtimestamp(s.st_mtime,dt.timezone.utc).isoformat(),'sha256':sha256(path,max_hash)}
    issues=[]; ext=path.suffix.lower()
    if s.st_size==0 and ext in LOG_EXT|DATA_EXT|MODEL_EXT:issues.append({'severity':'warning','code':'EMPTY_FILE','path':str(path),'evidence':'0 bytes'})
    if ext in LOG_EXT and s.st_size:
        for i,line in enumerate(tail(path),1):
            for name,pat in PATTERNS:
                if pat.search(line):
                    issues.append({'severity':'warning','code':'LOG_'+name,'path':str(path),'evidence':line[:240],'tail_line':i})
                    if len(issues)>=25:break
            if len(issues)>=25:break
    if ext in {'.csv','.tsv'} and 0<s.st_size<=max_data:
        try:
            with path.open(encoding='utf-8-sig',newline='') as f:
                reader=csv.reader(f,delimiter='\t' if ext=='.tsv' else ','); header=next(reader,None)
                if header:
                    if len(header)!=len(set(header)):issues.append({'severity':'warning','code':'DUPLICATE_HEADERS','path':str(path),'evidence':str(header[:30])})
                    n=0
                    for row in reader:
                        n+=1
                        if len(row)!=len(header):
                            issues.append({'severity':'warning','code':'ROW_WIDTH','path':str(path),'evidence':f'row {n+1}: {len(row)} fields vs {len(header)} headers'})
                            break
                    entry['data_rows_checked']=n
        except (UnicodeError,csv.Error,OSError) as e:issues.append({'severity':'warning','code':'CSV_READ','path':str(path),'evidence':str(e)})
    if ext=='.json' and 0<s.st_size<=max_data:
        try:
            with path.open(encoding='utf-8') as f:json.load(f)
        except (ValueError,UnicodeError,OSError) as e:issues.append({'severity':'warning','code':'JSON_PARSE','path':str(path),'evidence':str(e)})
    return entry,issues

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True);p.add_argument('--max-files',type=int,default=100000);p.add_argument('--hash-mb',type=int,default=8);p.add_argument('--parse-mb',type=int,default=16);a=p.parse_args()
    roots=[]
    for line in Path(a.config).read_text(encoding='utf-8').splitlines():
        line=line.strip()
        if line and not line.startswith('#'):roots.append(Path(line).expanduser().resolve())
    out=Path(a.out).expanduser().resolve();out.mkdir(parents=True,exist_ok=True)
    records=[];issues=[];count=0
    for root in roots:
        if not root.is_dir():issues.append({'severity':'error','code':'ROOT_UNAVAILABLE','path':str(root),'evidence':'not a readable directory'});continue
        def onerror(e):issues.append({'severity':'warning','code':'WALK_ERROR','path':getattr(e,'filename',''),'evidence':str(e)})
        for base,dirs,files in os.walk(root,followlinks=False,onerror=onerror):
            dirs[:]=[d for d in dirs if d not in IGNORE and not (Path(base)/d).is_symlink()]
            for name in files:
                path=Path(base)/name
                if path.is_symlink():continue
                try:
                    if not stat.S_ISREG(path.stat().st_mode):continue
                    entry,found=scan_file(path,a.hash_mb*1024*1024,a.parse_mb*1024*1024)
                    records.append(entry);issues.extend(found);count+=1
                except (OSError,UnicodeError) as e:issues.append({'severity':'warning','code':'FILE_READ','path':str(path),'evidence':str(e)})
                if count>=a.max_files:issues.append({'severity':'warning','code':'FILE_LIMIT','path':str(root),'evidence':f'limit {a.max_files} reached'});break
            if count>=a.max_files:break
        if count>=a.max_files:break
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    report={'generated_utc':now,'roots':[str(r) for r in roots],'files_scanned':len(records),'issues':issues,'files':records,'limitations':['No scientific metric recomputation or conclusion validation','Log keyword matches require human review','Files above size thresholds are not hashed or parsed','Only accessible regular files; symlinks skipped']}
    (out/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Research daily audit',f'Generated UTC: {now}',f'Files scanned: {len(records)}',f'Issues: {len(issues)}','','## Findings']
    for item in issues[:300]:lines.append(f"- **{item['severity']} / {item['code']}** `{item['path']}` — {item['evidence'].replace(chr(10),' ')[:240]}")
    if len(issues)>300:lines.append(f'- {len(issues)-300} more findings in audit.json')
    lines+=['','## Scope and limitations','This is a static inventory and heuristic check, not a full scientific audit. No project files were modified.']
    (out/'audit.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'files={len(records)} issues={len(issues)} output={out}')
if __name__=='__main__':main()
