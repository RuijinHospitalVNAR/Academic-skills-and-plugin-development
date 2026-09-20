#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skill-manager 台账与生命周期管理器 (ledger.py)

职责（确定性操作，供 skill-manager SKILL.md 流程调用，也可独立使用）：
  init            扫描 skills/ 目录初始化台账（增量补全，不覆盖已有记录）
  status [-v]     台账总览（active/merged/removed + 磁盘一致性检查）
  add <name> --source S --reason R [--provenance P --compare-report F --user-confirmed]
                  登记新技能入台账（吸收决策后调用）
  remove <name> --reason R [--dry-run --user-confirmed]
                  下架：三处删除(插件/用户级目录) + tar 备份 + 注册表清理 + 台账标记
  merge <src> <dst> --reason R   合并归档：src 移入 merged-away/，台账标记 merges_into
  audit [-n 20]   审计日志尾部
  batch <file>    批量：每行 "remove|add|merge <name> [dst] [--source S] --reason R"

约定：台账 data/skills-ledger.json（可改写），审计日志 data/audit-log.jsonl（只追加）。
"""
import argparse, json, shutil, tarfile, datetime, pathlib, re, sys

PLUGIN = pathlib.Path(__file__).resolve().parents[3]
SKILLS = PLUGIN / "skills"
DATA = PLUGIN / "data"
LEDGER = DATA / "skills-ledger.json"
AUDIT = DATA / "audit-log.jsonl"
USER_SKILL_DIRS = [pathlib.Path.home()/".trae-cn"/"skills", pathlib.Path.home()/".trae"/"skills"]

def now(): return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def load_ledger():
    if LEDGER.exists(): return json.loads(LEDGER.read_text())
    return {"meta": {"created": now(), "plugin": "protein-drug-design"}, "skills": {}}

def save_ledger(L):
    DATA.mkdir(exist_ok=True)
    LEDGER.write_text(json.dumps(L, ensure_ascii=False, indent=2) + "\n")

def log_audit(op, target, detail, user_confirmed=False):
    DATA.mkdir(exist_ok=True)
    with AUDIT.open("a") as f:
        f.write(json.dumps({"ts": now(), "op": op, "target": target, "detail": detail,
                            "actor": "agent", "user_confirmed": bool(user_confirmed)},
                           ensure_ascii=False) + "\n")

def fm_head(p):
    t = p.read_text()
    fm = t.split("---", 2)[1] if t.startswith("---") else ""
    return fm[fm.find("description:"):][:160]

def cmd_init(a):
    L = load_ledger(); n = 0
    for d in sorted(SKILLS.iterdir()):
        if d.is_dir() and (d/"SKILL.md").exists() and d.name not in L["skills"]:
            L["skills"][d.name] = {"status": "active", "date_added": now().split()[0],
                "source": "pre-existing(初始化扫描)", "provenance": "",
                "fm_desc_head": fm_head(d/"SKILL.md"),
                "merges_into": [], "absorbed_from": [], "trigger_notes": [],
                "decisions": [{"ts": now(), "decision": "init-scan", "reason": "目录初始化"}]}
            n += 1
    save_ledger(L)
    print(f"init: 新登记 {n} 条，台账共 {len(L['skills'])} 条")
    log_audit("init", "*", f"new={n} total={len(L['skills'])}")

def cmd_status(a):
    L = load_ledger()
    from collections import Counter
    c = Counter(v["status"] for v in L["skills"].values())
    print(f"台账: {sum(c.values())} 技能 = " + " | ".join(f"{k}:{v}" for k, v in c.items()))
    if a.verbose:
        for name, v in sorted(L["skills"].items()):
            mark = {"active":"OK","merged":"->"+(",".join(v["merges_into"]) or "?"),"removed":"DEL"}.get(v["status"],"?")
            print(f"  [{v['status']:>7}] {name:34s} {mark}")
    on_disk = {d.name for d in SKILLS.iterdir() if d.is_dir() and (d/"SKILL.md").exists()}
    active = {n for n, v in L["skills"].items() if v["status"] == "active"}
    if on_disk != active:
        print("!! 不一致 磁盘有台账无:", sorted(on_disk - active) or "-",
              "| 台账active磁盘无:", sorted(active - on_disk) or "-")

def cmd_add(a):
    d = SKILLS / a.name
    if not (d/"SKILL.md").exists(): sys.exit(f"X skills/{a.name}/SKILL.md 不存在")
    L = load_ledger()
    if L["skills"].get(a.name, {}).get("status") == "active": sys.exit(f"X {a.name} 已 active")
    L["skills"][a.name] = {"status": "active", "date_added": now().split()[0],
        "source": a.source, "provenance": a.provenance, "fm_desc_head": fm_head(d/"SKILL.md"),
        "merges_into": [], "absorbed_from": [], "trigger_notes": [],
        "decisions": [{"ts": now(), "decision": "absorb", "reason": a.reason,
                       "compare_report": a.compare_report}]}
    save_ledger(L)
    log_audit("add", a.name, f"source={a.source} reason={a.reason}", a.user_confirmed)
    print(f"+ add: {a.name}（后续: plugin.json keywords / install.sh 装机）")

def clean_registries(names, acts):
    wy = PLUGIN / "workflow.yaml"
    if wy.exists():
        t = wy.read_text(); orig = t
        for n in names:
            t = re.sub(rf"^\s*(skill|alternatives):.*\b{re.escape(n)}\b.*\n", "", t, flags=re.M)
        if t != orig: wy.write_text(t); acts.append("workflow.yaml 已清理")

def cmd_remove(a):
    L = load_ledger()
    if a.name not in L["skills"]: sys.exit(f"X 台账无 {a.name}")
    acts = []; d = SKILLS / a.name
    if d.exists():
        if a.dry_run: acts.append(f"[dry] 将删 {d}")
        else:
            bak = DATA/"removed-backup"/f"{a.name}-{now().split()[0]}.tar.gz"
            bak.parent.mkdir(parents=True, exist_ok=True)
            with tarfile.open(bak, "w:gz") as tf: tf.add(d, arcname=a.name)
            shutil.rmtree(d); acts.append(f"备份{bak.name}+已删插件目录")
    for ud in USER_SKILL_DIRS:
        p = ud/a.name
        if p.exists():
            if a.dry_run: acts.append(f"[dry] 将删 {p}")
            else: shutil.rmtree(p); acts.append(f"已删 {p}")
    if not a.dry_run:
        s = L["skills"][a.name]
        s["status"] = "removed"
        s["decisions"].append({"ts": now(), "decision": "remove", "reason": a.reason})
        save_ledger(L); clean_registries([a.name], acts)
        log_audit("remove", a.name, f"reason={a.reason}", a.user_confirmed)
    print(f"+ remove({a.name}): " + ("; ".join(acts) if acts else "目录已不在,仅台账标记"))

def cmd_merge(a):
    L = load_ledger()
    if a.src not in L["skills"] or a.dst not in L["skills"]: sys.exit("X src/dst 须已在台账")
    away = PLUGIN/"merged-away"
    if a.dry_run: print(f"[dry] mv skills/{a.src} -> merged-away/")
    else:
        away.mkdir(exist_ok=True)
        if (SKILLS/a.src).exists(): shutil.move(str(SKILLS/a.src), str(away/a.src))
        L["skills"][a.dst]["absorbed_from"].append(a.src)
        L["skills"][a.dst]["decisions"].append({"ts": now(), "decision": "merge-in", "from": a.src, "reason": a.reason})
        L["skills"][a.src]["status"] = "merged"; L["skills"][a.src]["merges_into"] = [a.dst]
        L["skills"][a.src]["decisions"].append({"ts": now(), "decision": "merge", "into": a.dst, "reason": a.reason})
        save_ledger(L)
        for ud in USER_SKILL_DIRS:
            p = ud/a.src
            if p.exists(): shutil.rmtree(p)
        log_audit("merge", f"{a.src}->{a.dst}", f"reason={a.reason}", a.user_confirmed)
    print(f"+ merge: {a.src} -> {a.dst}（正文合并完成后才执行本归档）")

def cmd_audit(a):
    if not AUDIT.exists(): print("(空)"); return
    for ln in AUDIT.read_text().strip().split("\n")[-a.n:]:
        r = json.loads(ln)
        print(f"{r['ts']} [{r['op']:>6}] {r['target']:36s} {r['detail'][:80]} (uc={r['user_confirmed']})")

def cmd_batch(a):
    for i, line in enumerate(pathlib.Path(a.file).read_text().split("\n"), 1):
        line = line.strip()
        if not line or line.startswith("#"): continue
        print(f"--- batch[{i}]: {line}")
        t = line.split()
        if t[0] == "remove":
            r = line.split("--reason", 1)
            cmd_remove(argparse.Namespace(name=t[1], reason=r[1].strip() if len(r)>1 else "batch", dry_run=False, user_confirmed=True))
        elif t[0] == "add":
            r = line.split("--reason", 1); s = line.split("--source", 1)
            cmd_add(argparse.Namespace(name=t[1],
                source=s[1].split()[0] if len(s)>1 else "batch",
                reason=r[1].strip() if len(r)>1 else "batch",
                provenance="", compare_report="", user_confirmed=True))
        elif t[0] == "merge" and len(t) > 3:
            r = line.split("--reason", 1)
            cmd_merge(argparse.Namespace(src=t[1], dst=t[2], reason=r[1].strip() if len(r)>1 else "batch", dry_run=False, user_confirmed=True))
        else: print("  (跳过)")

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("init")
    st = sp.add_parser("status"); st.add_argument("-v", "--verbose", action="store_true")
    ad = sp.add_parser("add"); ad.add_argument("name"); ad.add_argument("--source", required=True)
    ad.add_argument("--reason", required=True); ad.add_argument("--provenance", default="")
    ad.add_argument("--compare-report", default=""); ad.add_argument("--user-confirmed", action="store_true")
    rm = sp.add_parser("remove"); rm.add_argument("name"); rm.add_argument("--reason", required=True)
    rm.add_argument("--dry-run", action="store_true"); rm.add_argument("--user-confirmed", action="store_true")
    mg = sp.add_parser("merge"); mg.add_argument("src"); mg.add_argument("dst"); mg.add_argument("--reason", required=True)
    mg.add_argument("--dry-run", action="store_true"); mg.add_argument("--user-confirmed", action="store_true")
    au = sp.add_parser("audit"); au.add_argument("-n", type=int, default=20)
    ba = sp.add_parser("batch"); ba.add_argument("file")
    a = ap.parse_args()
    {"init": cmd_init, "status": cmd_status, "add": cmd_add, "remove": cmd_remove,
     "merge": cmd_merge, "audit": cmd_audit, "batch": cmd_batch}[a.cmd](a)

if __name__ == "__main__":
    main()
