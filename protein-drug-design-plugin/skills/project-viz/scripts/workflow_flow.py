#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""workflow_flow.py — workflow.yaml 管线配置递交给 mermaid flowchart

解析本插件 workflow.yaml 的 stages（缩进两层的 stage id + 行内注释 "# 阶段N: 名称" + skill 字段），
按阶段编号排序生成 flowchart LR：节点=阶段(skill)，主线（阶段1-5）连线带 outputs 标签，
科研全链路（阶段0a-8）虚线串联。

用法:
  python3 workflow_flow.py <workflow.yaml>              # 输出到 stdout
  python3 workflow_flow.py <workflow.yaml> --inplace out.md   # 刷新 markdown 的 VIZ 区

零第三方依赖（手工解析，不引 PyYAML）。
"""
import re
import sys

STAGE = re.compile(r"^  ([a-z0-9-]+):\s*#\s*阶段(\S+?)\s*[:：]\s*(.*)$")
SKILL = re.compile(r"^\s+skill:\s*(\S+)")
OUT = re.compile(r"^\s+-\s+([\w-]+):")
VIZ_BEGIN = "<!-- PIPELINE-VIZ -->"
VIZ_END = "<!-- /PIPELINE-VIZ -->"
MAINLINE_NUMS = {"1", "2", "3", "4", "5"}


def num_sort(num):
    m = re.match(r"(\d+)([ab]?)", num)
    return (int(m.group(1)), m.group(2))


def parse(path):
    stages, cur, section = [], None, ""
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        m = STAGE.match(line)
        if m:
            cur = {"id": m.group(1), "num": m.group(2), "name": m.group(3).strip(),
                   "skill": "", "outs": []}
            stages.append(cur)
            section = ""
            continue
        if cur is not None:
            s = SKILL.match(line)
            if s:
                cur["skill"] = s.group(1)
                continue
            # 跟踪当前键区块（inputs/outputs/proven_case...），只在 outputs 下取产物名
            km = re.match(r"^    (\w+):\s*$", line)
            if km:
                section = km.group(1)
                continue
            if section == "outputs":
                o = OUT.match(line)
                if o:
                    cur["outs"].append(o.group(1))
    return stages


def node(s):
    label = f"阶段{s['num']} {s['name']}"
    if s["skill"]:
        label += f"<br/>{s['skill']}"
    return f'    {s["id"]}["{label}"]'


def edge(a, b):
    outs = "、".join(dict.fromkeys(a["outs"]))[:28]
    if outs:
        return f'    {a["id"]} -->|"{outs}"| {b["id"]}'
    return f'    {a["id"]} --> {b["id"]}'


def build_flowchart(stages, title="蛋白质药物设计插件 · 端到端工作流"):
    stages = sorted(stages, key=lambda s: num_sort(s["num"]))
    mainline = [s for s in stages if s["num"] in MAINLINE_NUMS]
    others = [s for s in stages if s["num"] not in MAINLINE_NUMS]

    lines = ["flowchart LR", '    subgraph MAIN["计算主线（A9/VNAR 实证）"]']
    for s in mainline:
        lines.append(node(s))
    for a, b in zip(mainline, mainline[1:]):
        lines.append(edge(a, b))
    lines.append("    end")

    if others:
        lines.append('    subgraph CHAIN["科研全链路（收编技能）"]')
        for s in others:
            lines.append(node(s))
        for a, b in zip(others, others[1:]):
            lines.append(f"    {a['id']} -.- {b['id']}")
        lines.append("    end")
        if mainline and others:
            lines.append(f"    {mainline[-1]['id']} -.->|\"候选/数据\"| {others[0]['id']}")

    return "```mermaid\n" + "\n".join(lines) + "\n```"


def inplace(path, block):
    text = open(path, encoding="utf-8").read()
    wrapped = f"{VIZ_BEGIN}\n{block}\n{VIZ_END}"
    if VIZ_BEGIN in text and VIZ_END in text:
        text = re.sub(re.escape(VIZ_BEGIN) + r".*?" + re.escape(VIZ_END), wrapped, text, flags=re.S)
    else:
        text = text.rstrip("\n") + "\n\n" + wrapped + "\n"
    open(path, "w", encoding="utf-8").write(text)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    stages = parse(sys.argv[1])
    if not stages:
        sys.exit("no stages found")
    block = build_flowchart(stages)
    if "--inplace" in sys.argv:
        out = sys.argv[sys.argv.index("--inplace") + 1]
        inplace(out, block)
        print(f"refreshed PIPELINE-VIZ block in {out} ({len(stages)} stages)")
    else:
        print(block)


if __name__ == "__main__":
    main()
