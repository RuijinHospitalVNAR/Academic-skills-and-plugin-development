#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pre-commit 敏感信息扫描器 (secret-scan.py)
规则: 私钥块 / 各类 token / 公网 IP(排除本地段,版本号豁免) / 本机用户与数据路径
退出码 1 = 发现疑似泄漏, 阻止提交 (确信误报可 git commit --no-verify)
"""
import re, subprocess, sys, os

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

def main():
    repo = os.getcwd()
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                         capture_output=True, text=True).stdout
    findings = []
    for f in [x for x in out.split("\n") if x.strip()]:
        p = os.path.join(repo, f)
        if not os.path.isfile(p) or os.path.getsize(p) > 2_000_000: continue
        try: text = open(p, encoding="utf-8", errors="ignore").read()
        except Exception: continue
        for i, line in enumerate(text.split("\n"), 1):
            for pat, label in PATTERNS:
                m = re.search(pat, line)
                if not m: continue
                hit = m.group(0)
                if "IP" in label:
                    if IP_EXCLUDE.match(hit): continue
                    if not re.search(r"http|ssh|@|:\d{2,5}|host|server|端口|部署|deploy|tunnel|proxy", line.lower()):
                        continue  # 无网络上下文的 d.d.d.d 视为版本号
                findings.append(f"  {f}:{i}  [{label}]  {hit[:40]}")
            for pat, label in LOCAL_PATHS:
                m = re.search(pat, line)
                if m: findings.append(f"  {f}:{i}  [{label}]  {m.group(0)[:40]}")
    if findings:
        print("!! pre-commit 拦截: 疑似敏感信息 (%d 处)" % len(findings))
        print("\n".join(findings[:20]))
        print("\n处理: 改占位符/环境变量后重新 add+commit; 确信误报: git commit --no-verify")
        sys.exit(1)
    print("secret-scan: clean")
    sys.exit(0)

if __name__ == "__main__":
    main()
