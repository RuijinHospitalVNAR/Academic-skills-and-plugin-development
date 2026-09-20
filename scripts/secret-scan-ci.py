#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI 服务端敏感信息扫描器 (secret-scan-ci.py)

与本地 pre-commit 版 (secret-scan.py) 同一规则库；差异:
  - 输入源: 不读 git index, 而是扫描 (a) 当前工作区全部文本文件 (默认)
            (b) --history 模式: 全历史所有 blob 的每次出现 (防历史夹带)
  - 无交互逃生门: CI 发现即失败 (红叉), 强制修复
用法: python3 secret-scan-ci.py [--history]
"""
import re, subprocess, sys, os

# ===== 规则库 (与 scripts/secret-scan.py 保持同步: 改一处必须同步另一处) =====
PATTERNS = [
    (r"-----BEGIN (OPENSSH|RSA|EC|DSA|PGP) PRIVATE KEY-----", "私钥块"),
    (r"\bghp_[A-Za-z0-9]{30,}\b", "GitHub PAT"),
    (r"\bgho_[A-Za-z0-9]{30,}\b", "GitHub OAuth token"),
    (r"\bgithub_pat_[A-Za-z0-9_]{22,}\b", "GitHub fine-grained PAT"),
    (r"\bsk-[A-Za-z0-9]{20,}\b", "OpenAI/Anthropic key"),
    (r"\bAKIA[0-9A-Z]{16}\b", "AWS AccessKey"),
    (r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", "Slack token"),
    (r"\bhf_[A-Za-z0-9]{20,}\b", "HuggingFace token"),
    (r"\bAIza[0-9A-Za-z_\-]{35}\b", "Google API key"),
    (r"(?i)(password|passwd|secret|api_key|apikey|auth_token)\s*[=:]\s*['\"]?[A-Za-z0-9@#$%^&*+_]{12,}['\"]?\s*$", "硬编码凭证"),
    (r"(?<![\w.])(?:(?:2[0-4]\d|25[0-5]|1\d{2}|[1-9]?\d)\.){3}(?:2[0-4]\d|25[0-5]|1\d{2}|[1-9]?\d)(?![\w.])", "疑似IP(需确认)"),
]
IP_EXCLUDE = re.compile(r"^(0\.|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|255\.255\.255\.255)")
LOCAL_PATHS = [
    (r"/home/[a-z][a-z0-9_-]{2,}/", "本机用户路径(用<HOME>)"),
    (r"/data/wcf/[A-Za-z0-9_]", "本机数据路径(用占位符)"),
    (r"/data1?/Tools/", "本机工具路径(用占位符)"),
]
# CI 全历史扫描的豁免: vendored 第三方项目按惯例保留其内部内容
SKIP_PATH_SUBSTR = ["paperchecker-rules/", "node_modules/", ".git/"]

def scan_text(text, where, findings):
    for i, line in enumerate(text.split("\n"), 1):
        for pat, label in PATTERNS:
            m = re.search(pat, line)
            if not m: continue
            hit = m.group(0)
            if "IP" in label:
                if IP_EXCLUDE.match(hit): continue
                if not re.search(r"http|ssh|@|:\d{2,5}|host|server|端口|部署|deploy|tunnel|proxy", line.lower()):
                    continue
            findings.append(f"  {where}:{i}  [{label}]  {hit[:40]}")
        for pat, label in LOCAL_PATHS:
            m = re.search(pat, line)
            if m: findings.append(f"  {where}:{i}  [{label}]  {m.group(0)[:40]}")

def is_scannable(path):
    low = path.lower()
    if any(s in low for s in SKIP_PATH_SUBSTR): return False
    if low.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".tar.gz", ".gz", ".zip",
                     ".vsix", ".npy", ".npz", ".pdf", ".svg")): return False
    return True

def scan_worktree(root, findings):
    n = 0
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".git"]
        for fn in files:
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root)
            if not is_scannable(rel): continue
            if os.path.getsize(p) > 2_000_000: continue
            try: text = open(p, encoding="utf-8", errors="ignore").read()
            except Exception: continue
            n += 1
            scan_text(text, rel, findings)
    return n

def scan_history(findings):
    # 全历史 blob 逐一扫描 (rev-list --objects + cat-file)
    objs = subprocess.run(["git", "rev-list", "--objects", "--all"],
                          capture_output=True, text=True).stdout
    seen = set()
    n = 0
    for line in objs.split("\n"):
        parts = line.split(" ", 1)
        if len(parts) != 2 or not parts[1]: continue
        sha, path = parts
        if path in seen or not is_scannable(path): continue
        seen.add(path)
        blob = subprocess.run(["git", "cat-file", "blob", sha],
                              capture_output=True, text=True, errors="ignore")
        if blob.returncode != 0: continue
        n += 1
        scan_text(blob.stdout, f"[history]{path}", findings)
    return n

def main():
    root = os.getcwd()
    findings = []
    if "--history" in sys.argv:
        n = scan_history(findings)
        scope = f"全历史 {n} 个文件对象"
    else:
        n = scan_worktree(root, findings)
        scope = f"工作区 {n} 个文件"
    if findings:
        print(f"::error::CI 强制扫描拦截: {len(findings)} 处疑似敏感信息 ({scope})")
        for f in findings[:30]:
            print(f"::error::{f}")
        if len(findings) > 30: print(f"... 及另外 {len(findings)-30} 处")
        print("\n修复: 改占位符/环境变量; 若确系误报, 更新 secret-scan(-ci).py 的豁免规则后重跑")
        sys.exit(1)
    print(f"secret-scan-ci: clean ({scope})")
    sys.exit(0)

if __name__ == "__main__":
    main()
