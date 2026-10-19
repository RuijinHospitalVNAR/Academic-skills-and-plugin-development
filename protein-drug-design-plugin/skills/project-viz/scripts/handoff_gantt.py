#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""handoff_gantt.py — handoff.md 递交给 mermaid 进度时间线

解析 handoff 中的 "## 更新 (YYYY-MM-DD 第N轮 · 标题)" / "## 已完成 (YYYY-MM-DD)" 节标题，
生成 mermaid timeline（按日期分组的多轮事件）。

用法:
  python3 handoff_gantt.py <handoff.md>                 # 输出到 stdout
  python3 handoff_gantt.py <handoff.md> --inplace       # 插入/刷新 <!-- PROGRESS-VIZ --> 区
  python3 handoff_gantt.py <handoff.md> --gantt         # gantt 视图（排期/持续区间时用）

零第三方依赖。文本中的英文冒号已自动替换为全角（mermaid timeline 语法要求）。
"""
import re
import sys
import datetime

HDR = re.compile(r"^## (更新|已完成) \((\d{4}-\d{2}-\d{2})(?:\s+([^)·]+?))?(?:\s*·\s*([^)]+))?\)\s*$")
VIZ_BEGIN = "<!-- PROGRESS-VIZ -->"
VIZ_END = "<!-- /PROGRESS-VIZ -->"


def parse(path):
    events = []  # (date, round_label, title)
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = HDR.match(line.strip())
            if not m:
                continue
            kind, date, rnd, title = m.group(1), m.group(2), m.group(3), m.group(4)
            rnd = (rnd or "").strip()
            title = (title or "").strip()
            if kind == "已完成":
                label = rnd or "首轮"
            else:
                label = rnd or "更新"
            events.append((date, label, title))
    return events


def sanitize(text):
    """mermaid timeline 文本内禁英文冒号/引号"""
    return text.replace(":", "：").replace('"', "'").strip()


def build_timeline(events, title="项目演进"):
    lines = ["timeline", f"    title {sanitize(title)}"]
    for date, label, topic in events:
        segs = [sanitize(label)]
        if topic:
            segs.append(sanitize(topic))
        lines.append(f"    {date} : " + " : ".join(segs))
    return "```mermaid\n" + "\n".join(lines) + "\n```"


def build_gantt(events, title="项目进程"):
    # 每个事件占 1 天条；适合"里程碑"视图
    lines = ["gantt", f"    title {sanitize(title)}", "    dateFormat YYYY-MM-DD",
             "    axisFormat %m-%d", "    section 里程碑"]
    for i, (date, label, topic) in enumerate(events):
        name = sanitize(f"{label} {topic}".strip())[:24]
        d = datetime.date.fromisoformat(date)
        lines.append(f"    {name} :m{i}, {date}, {(d + datetime.timedelta(days=1)).isoformat()}")
    return "```mermaid\n" + "\n".join(lines) + "\n```"


def inplace(path, block):
    text = open(path, encoding="utf-8").read()
    wrapped = f"{VIZ_BEGIN}\n{block}\n{VIZ_END}"
    if VIZ_BEGIN in text and VIZ_END in text:
        text = re.sub(re.escape(VIZ_BEGIN) + r".*?" + re.escape(VIZ_END), wrapped, text, flags=re.S)
    else:
        # 插在首个二级标题（## 已完成）之后
        m = re.search(r"^## .+?$", text, flags=re.M)
        idx = m.end() if m else 0
        text = text[:idx] + "\n\n" + wrapped + "\n" + text[idx:]
    open(path, "w", encoding="utf-8").write(text)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    events = parse(path)
    if not events:
        sys.exit("no handoff round headers found")
    use_gantt = "--gantt" in sys.argv
    block = build_gantt(events) if use_gantt else build_timeline(events)
    if "--inplace" in sys.argv:
        inplace(path, block)
        print(f"refreshed PROGRESS-VIZ block in {path} ({len(events)} events)")
    else:
        print(block)


if __name__ == "__main__":
    main()
