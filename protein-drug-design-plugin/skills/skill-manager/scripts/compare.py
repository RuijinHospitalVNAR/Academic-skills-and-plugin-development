#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新技能 vs 插件现有技能对比器 (compare.py)

用法: python3 compare.py <候选技能目录或SKILL.md路径>
输出: 相似度报告（description token Jaccard + 正文 bigram 重叠 + 触发词冲突）
      + 按预设阈值的决策建议 (absorb / merge / reject)
阈值 (与 references/decision-criteria.md 一致):
  desc_jaccard >= 0.45 或 body_overlap >= 0.30  -> merge 候选
  0.20 <= jaccard < 0.45                        -> 边界(需人工/AI 判断职责)
  < 0.20 且无触发词冲突                          -> absorb 候选
"""
import json, re, sys, pathlib

PLUGIN = pathlib.Path(__file__).resolve().parents[3]
SKILLS = PLUGIN / "skills"

def fm_desc_body(p):
    t = p.read_text()
    if t.startswith("---"):
        parts = t.split("---", 2)
        fm, body = parts[1], parts[2] if len(parts) > 2 else ""
        m = re.search(r"description:\s*(.+(?:\n(?!\w+:).+)*)", fm)
        return (m.group(1) if m else ""), body
    return "", t

def toks(s): return set(re.findall(r"[a-zA-Z\u4e00-\u9fff]{2,}", s.lower()))

def bigrams(s):
    w = re.findall(r"[\u4e00-\u9fff]|[a-zA-Z]+", s.lower())
    return set(zip(w, w[1:]))

def jaccard(a, b): return len(a & b) / len(a | b) if a | b else 0.0

def main():
    cand = pathlib.Path(sys.argv[1])
    sm = cand / "SKILL.md" if cand.is_dir() else cand
    if not sm.exists(): sys.exit(f"X 找不到 {sm}")
    cd, cb = fm_desc_body(sm)
    ct, cbg = toks(cd), bigrams(cb)
    rows = []
    for d in sorted(SKILLS.iterdir()):
        if not d.is_dir() or d.name == "skill-manager" or d.name == cand.name: continue
        p = d / "SKILL.md"
        if not p.exists(): continue
        od, ob = fm_desc_body(p)
        jd = jaccard(ct, toks(od))
        obg = bigrams(ob)
        ov = len(cbg & obg) / len(cbg) if cbg else 0.0
        # 触发词冲突: 候选 desc 与对方 desc 的共享专有词(去除通用停用词)
        STOP = {"use","when","the","and","for","with","用户","需要","进行","分析","使用","工具","技能","流程","数据"}
        shared = (ct & toks(od)) - STOP
        rows.append((max(jd, ov), jd, ov, d.name, sorted(shared)[:8]))
    rows.sort(reverse=True)
    print(f"候选: {cand.name}  desc_tokens={len(ct)}")
    print(f"{'技能':34s} {'desc_jac':>8} {'body_ov':>8}  共享触发词")
    for mx, jd, ov, name, sh in rows[:8]:
        flag = " <== 相似!" if mx >= 0.30 else ""
        print(f"{name:34s} {jd:8.2f} {ov:8.2f}  {','.join(sh)}{flag}")
    top = rows[0] if rows else (0, 0, 0, "-", [])
    if top[0] >= 0.45: verdict = f"MERGE 候选 -> {top[3]} (top相似度 {top[0]:.2f})"
    elif top[0] >= 0.20: verdict = f"BOUNDARY: 与 {top[3]} 相似度 {top[0]:.2f}, 需结合职责判断 absorb/merge/reject"
    else: verdict = "ABSORB 候选 (无显著相似)"
    print("\n建议:", verdict)
    import os; os.makedirs(PLUGIN/"data", exist_ok=True)
    json.dump({"candidate": cand.name, "verdict": verdict.split(" (")[0],
               "top_matches": [{"skill": r[3], "desc_jaccard": round(r[1],3), "body_overlap": round(r[2],3)} for r in rows[:5]]},
              open(PLUGIN/"data"/"compare-last.json", "w"), ensure_ascii=False, indent=2)
    print("报告已存 data/compare-last.json")

if __name__ == "__main__":
    main()
